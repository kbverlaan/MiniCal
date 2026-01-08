import os
import requests
import json
from dotenv import load_dotenv
from app.config import BotConfig

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
        try:
            with open('app/prompts/qa_instructions.txt', 'r', encoding='utf-8') as f:
                user_context = f.read().strip()
                if user_context:
                    user_context = f"\n\n*Gebruikerscontext (gebruik waar relevant voor clarificatie):*\n{user_context}\n"
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Warning: Could not load user context: {e}")
        
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
REALISTISCHE SCHATTINGSRICHTLIJNEN (Nederlandse porties):

**BASIS INGREDIËNTEN:**
- Rijst (gekookt): Klein bord (150g) = 195 kcal, Normaal bord (200g) = 260 kcal, Groot bord (300g) = 390 kcal
- Pasta (gekookt): Klein bord (150g) = 235 kcal, Normaal bord (200g) = 310 kcal, Groot bord (300g) = 470 kcal
- Aardappelen: 1 middelgrote (150g) = 115 kcal, 3 middelgrote = 345 kcal
- Brood: 1 snee witbrood = 70 kcal, 1 snee volkorenbrood = 85 kcal

**EIWITTEN:**
- Kipfilet: Klein (100g) = 165 kcal (31g protein), Normaal (150g) = 248 kcal (47g protein), Groot (200g) = 330 kcal (62g protein)
- Gehakt: 100g = 250 kcal (20g protein, 18g vet)
- Ei: 1 ei = 75 kcal (6g protein, 5g vet)
- Zalm: 100g = 200 kcal (20g protein, 13g vet)
- Tonijn (blik in water): 100g = 130 kcal (30g protein)

**GROENTEN:**
- Sla/bladgroente: verwaarloosbaar (~10-20 kcal per portie)
- Tomaat: 1 middelgrote = 20 kcal
- Komkommer: halve = 25 kcal
- Broccoli: 100g = 35 kcal

**SAUZEN & TOEVOEGINGEN:**
- Mayonaise: 1 eetlepel = 100 kcal (11g vet)
- Ketchup: 1 eetlepel = 20 kcal
- Pesto: 1 eetlepel = 80 kcal (8g vet)
- Olijfolie: 1 eetlepel = 120 kcal (14g vet)
- Sojasaus: verwaarloosbaar (10 kcal per eetlepel)
- Sambal: verwaarloosbaar (5-10 kcal)

**DRANKEN:**
- Cola/frisdrank: Blikje (330ml) = 140 kcal, Fles (500ml) = 210 kcal
- Bier: Standaard (330ml) = 140 kcal
- Wijn: Glas (150ml) = 120 kcal
- Melk (vol): Glas (200ml) = 130 kcal

**SNACKS:**
- Banaan: 1 middelgrote = 105 kcal (27g carbs)
- Appel: 1 middelgrote = 95 kcal (25g carbs)
- Noten: Handje (30g) = 180 kcal (15g vet, 5g protein)

**VITAMINES & MINERALEN IN VOEDSEL:**

Algemeen principe: 
- Schat vitamines/mineralen ALLEEN als het voedsel een SIGNIFICANTE bron is (>10% dagelijkse behoefte)
- Voor supplementen: parse altijd de exacte dosering
- Zet 0 of laat leeg voor vitamines die niet significant aanwezig zijn

Vitamine D (mcg):
- Zalm 100g: 10-20 mcg
- Ei: 1-2 mcg per ei
- Supplement: parse exacte dosering (meestal 10-75 mcg)

Vitamine C (mg):
- Sinaasappel: 50 mg
- Paprika (rood, 100g): 130 mg
- Broccoli (100g): 90 mg
- Supplement: parse exacte dosering

Vitamine B12 (mcg):
- Vlees/vis (100g): 2-5 mcg
- Ei: 0.5 mcg
- Zuivel (glas melk): 1 mcg
- Supplement: parse exacte dosering

Omega-3 EPA+DHA (mg):
- Vette vis (zalm/makreel 100g): 1500-2500 mg
- Visolie supplement: parse exacte dosering (meestal 250-1000 mg)
- Algenolie: parse exacte dosering

Magnesium (mg):
- Spinazie (100g): 80 mg
- Noten (30g): 80 mg
- Volkoren brood (snee): 40 mg
- Supplement: parse exacte dosering (meestal 200-400 mg)

Calcium (mg):
- Melk/yoghurt (200ml): 240 mg
- Kaas (30g): 200 mg
- Broccoli (100g): 40 mg
- Supplement: parse exacte dosering

IJzer (mg):
- Rood vlees (100g): 2-3 mg
- Spinazie (100g): 2.7 mg
- Supplement: parse exacte dosering

Zink (mg):
- Rood vlees (100g): 4-5 mg
- Noten (30g): 1 mg
- Supplement: parse exacte dosering

Creatine (g):
- Rood vlees (100g): 0.3-0.4 g (meestal te weinig om significant te zijn)
- Supplement: parse exacte dosering (meestal 3-5 g)

**WORKOUTS (per uur, gemiddeld 85kg persoon):**
- Wandelen rustig: 220-280 kcal/uur
- Hardlopen (10 km/u): 680-790 kcal/uur
- Fietsen normaal: 450-560 kcal/uur
- Krachttraining matig: 340-450 kcal/uur
- Krachttraining intensief: 510-620 kcal/uur
- Zwemmen: 450-680 kcal/uur
- HIIT training: 560-790 kcal/uur

**BELANGRIJKE AANNAMES:**
- "Met saus" zonder specificatie → schat ROYAAL (1.5-2 eetlepels = 80-120 kcal gemiddeld)
- "Normaal bord/portie" = standaard Nederlandse portie, maar kies de BOVENKANT van de range
- Bij twijfel: kies de GROTERE optie (beter te hoog dan te laag schatten)
- Restaurant porties zijn vaak 1.5-2x groter dan thuis → bereken met 1.75x factor
- Snackrepen/chocolade: ~200-250 kcal per standaard reep
- Frituur/gefrituurde items: bereken extra 30% calorieën door frituurvet
- "Met kaas": schat minimaal 30g kaas = 120 kcal extra
- Bij onzekerheid: liever 10-15% te hoog schatten dan te laag

Retourneer ALLEEN valide JSON (geen markdown, geen backticks):
{
  "status": "complete" | "needs_clarification",
  "meals": [
    {
      "description": "Zeer specifieke beschrijving inclusief hoeveelheden (zodat dit als input kan hergebruikt worden, bijv: '2 gebakken eieren op 2 sneetjes volkorenbrood')",
      "calories": 650,
      "protein": 35.0,
      "carbs": 75.0,
      "fat": 18.0,
      "vitamin_d": 10.0,
      "vitamin_c": 50.0,
      "vitamin_b12": 2.5,
      "omega3": 1500.0,
      "magnesium": 80.0,
      "calcium": 240.0,
      "iron": 3.0,
      "zinc": 4.0,
      "creatine": 0.0
    }
  ],
  "workouts": [
    {
      "description": "Gedetailleerde beschrijving incl. intensiteit/snelheid (zodat dit als input kan hergebruikt worden, bijv: 'Hardlopen 10km/u')",
      "duration_minutes": 60,
      "calories_burned": 280
    }
  ],
  "clarification_question": "Optionele vraag of vragen bij needs_clarification (mag meerdere vragen in één string zijn)",
  "summary": "Optionele samenvatting bij complete: leg uit HOE je de calorieën/macros hebt berekend. Bijvoorbeeld: '2 eieren (150 kcal) + 2 sneetjes volkorenbrood (170 kcal) + 1 banaan (105 kcal) = 425 kcal totaal'. Wees specifiek en transparant in de berekening."
}"""

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

*Je Aanpak:*
- *Analyseer de Waarom*: Leg fysiologische mechanismen uit waar relevant (bijv. waarom protein belangrijk is voor herstel)
- *Geef Concrete Protocollen*: Vertaal inzichten naar praktische stappen (bijv. timing van maaltijden, workout planning)
- *Houd Rekening met Context*: Pas advies aan op basis van recente workouts, energieniveau, doelen
- *Gebruik Hiërarchie*: Onderscheid essentials (calorieën, protein) van optimalisaties (micronutriënten, timing)
- *9+ Keuzes*: Geef realistisch, duurzaam advies dat 90% van de winst oplevert

*Focusgebieden:*
Training • Herstel • Voeding • Slaap • Stressregulatie • Focus

*Data die je krijgt:*
1. De vraag van de gebruiker
2. Dagelijkse doelen en huidige intake (vandaag + weekgemiddelde)
3. Workout historie van de afgelopen 7 dagen
4. Health metrics: Slaap, Hartslag, Stress (van Garmin)
5. Eerdere conversatie (indien beschikbaar)

*Health Metrics Interpretatie:*
SLAAP:
- 7-9u = optimaal voor herstel
- Deep sleep = belangrijkst voor fysieke recovery
- REM sleep = belangrijk voor mentale recovery
- Sleep score <70 = slechte nacht, advies rest day

HARTSLAG:
- Resting HR: lager = beter hersteld (40-60 = atleet level)
- Verhoogde resting HR = mogelijk overtraining/ziekte
- HRV (Heart Rate Variability): hoger = beter hersteld

STRESS:
- <25 = laag (goed!)
- 25-50 = gemiddeld
- 50-75 = hoog (meer rust nodig)
- >75 = zeer hoog (actie vereist)

*Antwoordstijl:*
- *BONDIG*: Max 4-5 alinea's (korte paragrafen)
- Gebruik concrete cijfers uit de data
- Leg het _waarom_ uit bij advies (mechanisme)
- Geef praktische stappen (protocol)
- Vergelijk huidige prestaties met doelen
- Gebruik emojis voor leesbaarheid
- Correleer health metrics met performance (bijv. "Slechte slaap + zware training gisteren = rust vandaag")

*TELEGRAM MARKDOWN (BELANGRIJK):*
- Gebruik *tekst* voor bold (enkele sterren)
- Gebruik _tekst_ voor italic (enkele underscores)
- VERBODEN: ** (dubbele sterren), __ (dubbele underscores), ### (headers), > (quotes), ``` (code blocks)
- Houd het simpel: vooral gewone tekst met af en toe *nadruk* en emojis 💪

*Voorbeelden:*

Vraag: "Hoe gaat het deze week?"
→ "Deze week zit je gemiddeld op 2150 kcal per dag (doel: 2000) en 145g protein 💪. Vandaag 1850 kcal en 140g protein. Je zit consistent rond je doel - goed bezig!"

Vraag: "Haal ik genoeg protein?"
→ "Deze week gemiddeld 145g protein/dag, vandaag 140g. Voor spiergroei en herstel wordt 1.6-2.2g per kg lichaamsgewicht aanbevolen (_mechanisme_: stimuleert muscle protein synthesis). Bij ~85kg zit je ruim goed! 💪"

Vraag: "Hoe moet ik mijn workouts plannen?"
→ "Je hebt 3 dagen achter elkaar getraind (legs, push, cardio). Herstel is cruciaal voor adaptatie - zonder rust geen vooruitgang. *Protocol*: vandaag rustdag of lichte mobility work (wandelen 20-30 min). Morgen kun je weer volledig hersteld aanpakken. 🧘‍♂️"

Vraag: "Wat zijn verbeterpunten?"
→ "Je calorieën en protein zijn consistent op doel ✅. *Verbeterpunt*: Je omega-3 intake is laag (gemiddeld 200mg vs aanbevolen 250-500mg EPA+DHA voor ontstekingsremming en herstel). Simpele fix: 2x/week vette vis of dagelijks visolie supplement. 🐟"

Blijf wetenschappelijk onderbouwd, praktisch en motiverend.{extra_instructions}"""

        # Format the stats data for the LLM
        stats_context = f"""**DAGELIJKSE DOELEN:**
- Calorieën: {user_goals.get('daily_calories', 'Niet ingesteld')} kcal
- Protein: {user_goals.get('daily_protein', 'Niet ingesteld')}g
- Carbs: {user_goals.get('daily_carbs', 'Niet ingesteld')}g
- Vet: {user_goals.get('daily_fat', 'Niet ingesteld')}g

**VANDAAG:**
- Calorieën: {daily_stats['total_calories']} kcal (netto: {daily_stats['net_calories']} kcal)
- Protein: {daily_stats['total_protein']:.1f}g
- Carbs: {daily_stats['total_carbs']:.1f}g
- Vet: {daily_stats['total_fat']:.1f}g
- Verbrand: {daily_stats['total_burned']} kcal
- Maaltijden: {daily_stats['meal_count']}
- Workouts: {daily_stats['workout_count']}

**VITAMINES/MINERALEN VANDAAG:**
- Vitamine D: {daily_stats.get('vitamin_d', 0):.1f} mcg
- Vitamine C: {daily_stats.get('vitamin_c', 0):.0f} mg
- Vitamine B12: {daily_stats.get('vitamin_b12', 0):.1f} mcg
- Omega-3: {daily_stats.get('omega3', 0):.0f} mg
- Magnesium: {daily_stats.get('magnesium', 0):.0f} mg
- Calcium: {daily_stats.get('calcium', 0):.0f} mg
- IJzer: {daily_stats.get('iron', 0):.1f} mg
- Zink: {daily_stats.get('zinc', 0):.1f} mg
- Creatine: {daily_stats.get('creatine', 0):.1f} g

**DEZE WEEK (gemiddeld per dag, afgelopen {weekly_stats.get('days_in_range', 7)} dagen):**
- Calorieën: {weekly_stats.get('avg_calories', 0):.0f} kcal (netto: {weekly_stats.get('avg_net_calories', 0):.0f} kcal)
- Protein: {weekly_stats.get('avg_protein', 0):.1f}g
- Carbs: {weekly_stats.get('avg_carbs', 0):.1f}g
- Vet: {weekly_stats.get('avg_fat', 0):.1f}g
- Verbrand: {weekly_stats.get('avg_burned', 0):.0f} kcal
- Totaal maaltijden: {weekly_stats.get('total_meals', 0)}
- Totaal workouts: {weekly_stats.get('total_workouts', 0)}

**VITAMINES/MINERALEN WEEKGEMIDDELDE:**
- Vitamine D: {weekly_stats.get('avg_vitamin_d', 0):.1f} mcg/dag
- Vitamine C: {weekly_stats.get('avg_vitamin_c', 0):.0f} mg/dag
- Vitamine B12: {weekly_stats.get('avg_vitamin_b12', 0):.1f} mcg/dag
- Omega-3: {weekly_stats.get('avg_omega3', 0):.0f} mg/dag
- Magnesium: {weekly_stats.get('avg_magnesium', 0):.0f} mg/dag
- Calcium: {weekly_stats.get('avg_calcium', 0):.0f} mg/dag
- IJzer: {weekly_stats.get('avg_iron', 0):.1f} mg/dag
- Zink: {weekly_stats.get('avg_zinc', 0):.1f} mg/dag
- Creatine: {weekly_stats.get('avg_creatine', 0):.1f} g/dag"""

        if recent_workouts:
            stats_context += "\n\n**WORKOUT HISTORIE (Afgelopen 7 dagen):**\n"
            for w in recent_workouts:
                stats_context += f"- {w.get('date')}: {w.get('activity')} ({w.get('calories_burned')} kcal)\n"
        
        # Add health metrics (sleep, HR, stress)
        if health_metrics:
            sleep_logs = health_metrics.get('sleep', [])
            hr_logs = health_metrics.get('heart_rate', [])
            stress_logs = health_metrics.get('stress', [])
            
            if sleep_logs:
                stats_context += "\n\n**SLAAP TRACKING (Recent):**\n"
                for s in sleep_logs[:7]:  # Last 7 days
                    total = s.get('total_hours', 0)
                    deep = s.get('deep_hours', 0)
                    light = s.get('light_hours', 0)
                    rem = s.get('rem_hours', 0)
                    score = s.get('quality_score')
                    stats_context += f"- {s.get('date')}: {total:.1f}u totaal"
                    if deep or light or rem:
                        stats_context += f" (Deep: {deep:.1f}u, Light: {light:.1f}u, REM: {rem:.1f}u)"
                    if score:
                        stats_context += f" - Score: {score}/100"
                    stats_context += "\n"
            
            if hr_logs:
                stats_context += "\n**HARTSLAG (Recent):**\n"
                for h in hr_logs[:7]:
                    resting = h.get('resting_hr')
                    avg = h.get('avg_hr')
                    max_hr = h.get('max_hr')
                    hrv = h.get('hrv_avg')
                    stats_context += f"- {h.get('date')}: "
                    if resting:
                        stats_context += f"Resting {resting} bpm"
                    if avg:
                        stats_context += f", Avg {avg} bpm"
                    if hrv:
                        stats_context += f", HRV {hrv} ms"
                    stats_context += "\n"
            
            if stress_logs:
                stats_context += "\n**STRESS LEVELS (Recent):**\n"
                for st in stress_logs[:7]:
                    avg_stress = st.get('avg_stress')
                    max_stress = st.get('max_stress')
                    if avg_stress is not None:
                        stats_context += f"- {st.get('date')}: Avg {avg_stress}/100"
                        if max_stress:
                            stats_context += f", Max {max_stress}/100"
                        stats_context += "\n"

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
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
