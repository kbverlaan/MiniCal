import os
import requests
import json
from dotenv import load_dotenv
from app.config import BotConfig
from app.services.stats_formatter import StatsFormatter

load_dotenv()

class LLMService:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY must be set in environment variables.")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/kbverlaan/MiniCal',
            'X-Title': 'MiniCal'
        }

    def classify_intent(self, text: str, conversation_history: list = None) -> dict:
        """
        Classify if the user input is a question or data to log.
        
        Args:
            text: Current user message
            conversation_history: List of previous messages
        
        Returns: {
            "intent": "question" | "log_data" | "clarification_response",
            "confidence": 0.0-1.0
        }
        """
        
        system_prompt = """Je bent een slimme intent classifier voor een voedingstracking app.

Je taak: Bepaal of de gebruiker:
1. **QUESTION**: Een vraag stelt, om advies vraagt, reflecteert of in gesprek is
2. **LOG_DATA**: ACTIEF iets wil loggen (maaltijd, workout, supplement) - moet concrete data bevatten

🔍 **QUESTION** herken je aan:
- Vraagwoorden: hoe, wat, hoeveel, waarom, wanneer + ?
- Adviesvragen: "tips", "verbeterpunten", "wat denk je"
- Reflectie/plannen: "ik ga...", "ik denk dat...", "misschien moet ik..."
- Conversationeel: vervolg op eerdere discussie zonder concrete data
- Evaluatie: "dit werkt (niet)", "ik merk dat...", "ik voel..."

✅ **LOG_DATA** herken je aan:
- Concrete voedsel: "2 eieren", "pizza margherita", "300g kipfilet"
- Concrete workout: "1 uur hardlopen", "benchpress 3x8", "leg day"
- Concrete supplement: "creatine 5g", "vitamine D3 1000mcg"
- Tijdsindicatie + voedsel/workout: "ontbijt: havermout", "net gesport"
- Korte clarification antwoorden: "200 gram", "normaal bord", "met mayo"

❌ **NIET log_data** (maar question):
- "Ik denk dat ik het altijd ga doen na het eten" → reflectie/plan
- "Dit werkt goed voor mij" → evaluatie
- "Misschien moet ik meer protein eten" → overweging
- "Ik ga proberen meer te bewegen" → intentie
- "Vaak heb ik nog honger 's avonds" → observatie

Voorbeelden QUESTION:
- "Hoe gaat het deze week?"
- "Haal ik genoeg protein?"
- "Heb je tips voor mij?"
- "Ik denk dat ik het gewoon altijd ga doen ook na het avondeten"
- "Dit werkt goed, ik merk verschil"
- "Misschien moet ik eerder ontbijten"

Voorbeelden LOG_DATA:
- "2 eieren met toast"
- "Pizza margherita gegeten"
- "1 uur hardlopen gedaan"
- "Creatine 5g genomen"
- "Ontbijt: havermout met banaan"
- "200 gram" (clarification)
- "Normaal bord" (clarification)

Retourneer ALLEEN valide JSON:
{
  "intent": "question" | "log_data",
  "confidence": 0.95
}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            # Include last 4 messages for context
            messages.extend(conversation_history[-4:])
        
        messages.append({"role": "user", "content": text})

        payload = {
            'model': BotConfig.MODEL_INTENT_CLASSIFICATION,
            'messages': messages,
            'response_format': {'type': 'json_object'},
            'temperature': 0.1,
            'max_tokens': 100
        }

        print(f"\n=== INTENT CLASSIFICATION ===")
        print(f"Model: {payload['model']}")
        print(f"User message: {text}")
        print(f"History messages: {len(conversation_history) if conversation_history else 0}")

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result['choices'][0]['message']['content']
                
                # Clean markdown
                llm_response = llm_response.strip()
                if llm_response.startswith('```json'):
                    llm_response = llm_response[7:]
                if llm_response.startswith('```'):
                    llm_response = llm_response[3:]
                if llm_response.endswith('```'):
                    llm_response = llm_response[:-3]
                llm_response = llm_response.strip()
                
                parsed = json.loads(llm_response)
                
                # Validate
                if 'intent' not in parsed:
                    parsed['intent'] = 'log_data'  # Default fallback
                if 'confidence' not in parsed:
                    parsed['confidence'] = 0.5
                
                print(f"Intent result: {parsed['intent']} (confidence: {parsed['confidence']})")
                print(f"==========================\n")
                
                return parsed
            else:
                print(f"LLM Error (intent): {response.status_code} - {response.text}")
                return {"intent": "log_data", "confidence": 0.5}
                
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return {"intent": "log_data", "confidence": 0.5}

    def parse_food_and_workouts(self, text: str, conversation_history: list = None) -> dict:
        """
        Parse user text into meals and workouts using LLM.
        
        Args:
            text: Current user message
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
        
        Returns: {
            "status": "complete" | "needs_clarification",
            "meals": [...],
            "workouts": [...],
            "clarification_question": "..." (optional),
            "summary": "..." (optional)
        }
        """
        
        # Load user profile from qa_instructions.txt for context
        user_context = ""
        knowledge_base = ""
        try:
            with open('app/prompts/qa_instructions.txt', 'r', encoding='utf-8') as f:
                user_context = f.read().strip()
                if user_context:
                    user_context = f"\n\n*Gebruikerscontext (gebruik waar relevant voor clarificatie):*\n{user_context}\n"
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Warning: Could not load user context: {e}")

        try:
            with open('app/prompts/knowledge_base.txt', 'r', encoding='utf-8') as f:
                knowledge_base = f.read().strip()
                if knowledge_base:
                    knowledge_base = f"\n\n*Kennisbank:*\n{knowledge_base}\n"
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")
        
        system_prompt = f"""Je bent een expert voedings- en fitness assistent die zeer nauwkeurig maaltijden en workouts analyseert.

Je taak:
1. Analyseer de gebruikersinput voor maaltijden en/of workouts
2. Schat calorieën en macros ZO ACCURAAT MOGELIJK
3. Schat ook vitamines, mineralen en supplementen die in het voedsel zitten OF als supplement zijn ingenomen
4. Bepaal of je meer informatie nodig hebt voor een goede schatting
5. Houd context bij - als de gebruiker eerder een vraag heeft beantwoord, gebruik die info

Beslissingslogica:
- **COMPLETE**: Informatie is verwerkt.
  * Als er maaltijden/workouts zijn: bereken en geef korte samenvatting in 'summary'.
  * Als er ECHT geen data te vinden is (bijv. "test" of random tekst): return empty meals/workouts arrays.
- **NEEDS_CLARIFICATION**: Essentiële details ontbreken voor accurate schatting → stel slimme, specifieke vraag (of vragen)
  * Focus op: portiegroottes, bereidingswijze, type ingrediënten, intensiteit workout
  * *Gebruik gebruikerscontext waar relevant*: bijv. als gebruiker in cut zit, vraag naar exactere porties. Als workout info nodig is, hou rekening met trainingsschema.
  * Je mag MEERDERE vragen in één keer stellen voor een complete schatting
  * Je mag ook MEERDERE opvolgvragen over meerdere exchanges stellen
  * Voorbeeld: "Hoeveel rijst ongeveer (klein/normaal/groot bord)? En met welke saus (en hoeveel)?"

BELANGRIJK: Als het duidelijk een vraag is (niet data loggen), geef dan gewoon COMPLETE terug met lege arrays. De intent classifier haalt deze er normaal al uit.

{user_context}
{knowledge_base}

Retourneer ALLEEN valide JSON (geen markdown, geen backticks):
{{
  "_thought_process": "Kort intern redeneringproces. Analyseer wat ontbreekt, check persoonlijke context (bijv. is het een cut fase?), vergelijk met kennisbank richtlijnen en besluit of clarificatie nodig is of dat je een aanname mag doen.",
  "status": "complete" | "needs_clarification",
  "meals": [
    {{
      "description": "Zeer specifieke beschrijving inclusief hoeveelheden (zodat dit als input kan hergebruikt worden, bijv: 2 gebakken eieren op 2 sneetjes volkorenbrood)",
      "calories": 650,
      "protein": 35.0,
      "carbs": 75.0,
      "fat": 18.0,
      "fiber": 5.0,
      "sugar": 8.0,
      "saturated_fat": 3.0,
      "vitamin_d": 10.0,
      "vitamin_c": 50.0,
      "vitamin_b12": 2.5,
      "omega3_ala": 0.0,
      "omega3_epa_dha": 1500.0,
      "magnesium": 80.0,
      "calcium": 240.0,
      "iron": 3.0,
      "zinc": 4.0,
      "creatine": 0.0
    }}
  ],
  "workouts": [
    {{
      "description": "Gedetailleerde beschrijving incl. intensiteit/snelheid (zodat dit als input kan hergebruikt worden, bijv: Hardlopen 10km/u)",
      "duration_minutes": 60,
      "calories_burned": 280
    }}
  ],
  "clarification_question": "Optionele vraag of vragen bij needs_clarification (mag meerdere vragen in één string zijn)",
  "summary": "Optionele samenvatting bij complete: leg uit HOE je de calorieën/macros hebt berekend. Bijvoorbeeld: 2 eieren (150 kcal) + 2 sneetjes volkorenbrood (170 kcal) + 1 banaan (105 kcal) = 425 kcal totaal. Wees specifiek en transparant in de berekening."
}}"""

        # Build messages array with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": text})

        payload = {
            'model': BotConfig.MODEL_FOOD_PARSING,
            'messages': messages,
            'response_format': {'type': 'json_object'},
            'temperature': 0.2,  # Lagere temp voor consistentere output
            'max_tokens': 8192  # Increased for reasoning models
        }

        print(f"\n=== FOOD/WORKOUT PARSING ===")
        print(f"Model: {payload['model']}")
        print(f"User message: {text}")
        print(f"History messages: {len(conversation_history) if conversation_history else 0}")

        try:
            # Increased timeout for reasoning models
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for API error in response
                if 'error' in result:
                    print(f"LLM API Error: {result['error']}")
                    return {"status": "complete", "meals": [], "workouts": []}
                
                if 'choices' not in result or not result['choices']:
                    print(f"LLM Unexpected Response (no choices): {result}")
                    return {"status": "complete", "meals": [], "workouts": []}
                
                llm_response = result['choices'][0]['message']['content']
                
                if not llm_response:
                    print(f"LLM Empty Response Content. Full result: {result}")
                    return {"status": "complete", "meals": [], "workouts": []}
                
                # Debug: print raw response
                print(f"LLM Raw Response: {llm_response[:200]}...")
                
                # Clean markdown code blocks if present
                llm_response = llm_response.strip()
                if llm_response.startswith('```json'):
                    llm_response = llm_response[7:]  # Remove ```json
                if llm_response.startswith('```'):
                    llm_response = llm_response[3:]  # Remove ```
                if llm_response.endswith('```'):
                    llm_response = llm_response[:-3]  # Remove trailing ```
                llm_response = llm_response.strip()
                
                # Parse JSON
                parsed = json.loads(llm_response)
                
                # Validate structure
                if 'status' not in parsed:
                    parsed['status'] = 'complete'  # Default
                if 'meals' not in parsed:
                    parsed['meals'] = []
                if 'workouts' not in parsed:
                    parsed['workouts'] = []
                
                print(f"Parsing result: status={parsed['status']}, meals={len(parsed['meals'])}, workouts={len(parsed['workouts'])}")
                if parsed.get('clarification_question'):
                    print(f"Clarification: {parsed['clarification_question']}")
                print(f"============================\n")
                
                return parsed
            else:
                print(f"LLM Error: {response.status_code} - {response.text}")
                return {"status": "complete", "meals": [], "workouts": []}
                
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Response text: {llm_response if 'llm_response' in locals() else 'N/A'}")
            return {"status": "complete", "meals": [], "workouts": []}
        except Exception as e:
            print(f"Error parsing with LLM: {e}")
            return {"status": "complete", "meals": [], "workouts": []}

    def answer_question_with_stats(self, question: str, daily_stats: dict, weekly_stats: dict, user_goals: dict = None, recent_workouts: list = None, health_metrics: dict = None, conversation_history: list = None) -> str:
        """
        Answer user questions using their daily and weekly statistics.
        
        Args:
            question: User's question
            daily_stats: Today's totals from get_daily_totals()
            weekly_stats: Weekly averages from get_weekly_averages()
            user_goals: User's daily goals (calories, protein, carbs, fat)
            recent_workouts: List of workout dictionaries from last 7 days
            health_metrics: Dict with sleep, heart_rate, stress data
            conversation_history: List of previous messages
        
        Returns:
            Natural language answer to the question
        """
        
        # Load extra instructions from file if available
        extra_instructions = ""
        try:
            with open('app/prompts/qa_instructions.txt', 'r', encoding='utf-8') as f:
                extra_instructions = f.read().strip()
                if extra_instructions:
                    extra_instructions = f"\n\n*Extra Instructies:*\n{extra_instructions}"
        except FileNotFoundError:
            pass  # File doesn't exist yet, skip
        except Exception as e:
            print(f"Warning: Could not load qa_instructions.txt: {e}")
        
        system_prompt = f"""Je bent een Performance & Health Analyst — een data-gedreven assistent voor het optimaliseren van fysieke prestaties en gezondheid.

*Je Rol & Expertise:*
Jij bent niet zomaar een chatbot, jij bent een coach. Je analyseert de data (voeding, slaap, training) om de gebruiker te helpen excelleren. Je focus ligt op de synergie tussen training, herstel en voeding.

*Je Aanpak:*
- *Diepgang met Context*: Antwoord niet generiek. Gebruik de specifieke data (trends, herstelscores, recente workouts) om je advies op maat te maken.
- *Het 'Waarom'*: Leg kort de fysiologische reden uit achter je advies (bijv. "Eiwit is nu essentieel voor mTOR activatie na je training").
- *Concrete Protocollen*: Vertaal data naar actie. Geef duidelijke stappen (bijv. "Eet nu nog 20g eiwitten en ga vroeg naar bed").
- *Essentials First*: Focus op wat echt telt (calorieën, eiwit, slaap) voordat je op details ingaat.

*Antwoordstijl:*
- *Direct & Bondig*: Geen lange inleidingen. Kom tot de kern.
- *Professioneel & Motiverend*: Je bent een expert. Spreek met autoriteit maar blijf bemoedigend.
- *Gebruik de Data*: Noem de specifieke cijfers in je antwoord om je punt te maken.

*TELEGRAM FORMATTING REGELS (STRIKT):*
- Gebruik *tekst* voor nadruk (bold) - ALTIJD sluiten met *
- Gebruik GEEN underscores _ - deze breken formatting
- Gebruik GEEN dubbele asterisks ** 
- Gebruik GEEN andere markdown: # > ``` [] ()
- Bullets: gebruik gewoon - (dash + spatie)
- Getallen/eenheden: schrijf normaal (1000 kcal, niet 1000kcal)
- Check ALTIJD: elke * die je opent moet je ook sluiten

{extra_instructions}"""

        # Generate smart stats context using the new formatter
        stats_context = StatsFormatter.format(
            daily_stats=daily_stats,
            weekly_stats=weekly_stats,
            user_goals=user_goals,
            recent_workouts=recent_workouts,
            health_metrics=health_metrics
        )

        messages = [{"role": "system", "content": system_prompt}]        # Add conversation history if provided
        if conversation_history:
            limit = BotConfig.MAX_HISTORY_MESSAGES
            messages.extend(conversation_history[-limit:])

        messages.append({"role": "user", "content": f"MIJN DATA:\n{stats_context}\n\nMIJN VRAAG:\n{question}"})

        payload = {
            'model': BotConfig.MODEL_QUESTION_ANSWERING,
            'messages': messages,
            'temperature': 0.3,  # Iets hoger voor natuurlijkere antwoorden
            'max_tokens': 8192  # Increased for reasoning models
        }

        print(f"\n=== QUESTION ANSWERING ===")
        print(f"Model: {payload['model']}")
        print(f"Question: {question}")
        print(f"History messages: {len(conversation_history) if conversation_history else 0}")
        print(f"Stats context length: {len(stats_context)} chars")

        try:
            # Increased timeout for reasoning models
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip()
                print(f"Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")
                print(f"==========================\n")
                return answer
            else:
                print(f"LLM Error (question): {response.status_code} - {response.text}")
                return "❌ Sorry, ik kon je vraag niet beantwoorden. Probeer het opnieuw."
                
        except Exception as e:
            print(f"Error answering question with LLM: {e}")
            return "❌ Er ging iets fout bij het beantwoorden van je vraag."

# Global instance
llm_service = LLMService()
