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
1. **QUESTION**: Een vraag stelt over hun statistieken/voortgang
2. **LOG_DATA**: Maaltijd, workout of supplement wil loggen
3. **CLARIFICATION_RESPONSE**: Antwoord geeft op een eerdere vraag van de assistent

Voorbeelden QUESTION:
- "Hoe gaat het deze week?"
- "Haal ik genoeg protein?"
- "Hoeveel heb ik gesport?"
- "Zit ik op schema?"
- "Wat zijn mijn gemiddeldes?"
- "Heb je nog tips voor mij?"
- "Wat kan ik verbeteren?"
- "Geef advies op basis van mijn data"

Voorbeelden LOG_DATA:
- "2 eieren met toast"
- "Pizza margherita gegeten"
- "Uurtje hardlopen gedaan"
- "Vitamine D3 1000mcg genomen"
- "Ontbijt: havermout met banaan"

Voorbeelden CLARIFICATION_RESPONSE (als context eerdere vraag van assistent bevat):
- "Ongeveer 200 gram" (antwoord op: "Hoeveel rijst?")
- "Normaal bord" (antwoord op: "Klein of groot bord?")
- "Met mayonaise" (antwoord op: "Met welke saus?")

Belangrijk:
- Als conversation_history eindigt met een vraag van de assistent → waarschijnlijk CLARIFICATION_RESPONSE
- Korte antwoorden na assistent vragen = CLARIFICATION_RESPONSE
- Vraagwoorden (hoe, wat, hoeveel) + '?' = meestal QUESTION
- Vragen om advies, tips of verbeterpunten = QUESTION
- Voedsel/activiteit beschrijvingen = LOG_DATA

Retourneer ALLEEN valide JSON:
{
  "intent": "question" | "log_data" | "clarification_response",
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
        
        system_prompt = """Je bent een expert voedings- en fitness assistent die zeer nauwkeurig maaltijden en workouts analyseert.

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
- **NEEDS_CLARIFICATION**: Essentiële details ontbreken voor accurate schatting → stel slimme, specifieke vraag
  * Focus op: portiegroottes, bereidingswijze, type ingrediënten, intensiteit workout
  * Vraag alleen naar ESSENTIËLE info, geen perfectie
  * Je mag MEERDERE opvolgvragen stellen om tot een accurate schatting te komen
  * Voorbeeld: "Hoeveel rijst ongeveer? Een klein of groot bord?"

BELANGRIJK: Als het duidelijk een vraag is (niet data loggen), geef dan gewoon COMPLETE terug met lege arrays. De intent classifier haalt deze er normaal al uit.

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

**WORKOUTS (per uur, gemiddeld 75kg persoon):**
- Wandelen rustig: 200-250 kcal/uur
- Hardlopen (10 km/u): 600-700 kcal/uur
- Fietsen normaal: 400-500 kcal/uur
- Krachttraining matig: 300-400 kcal/uur
- Krachttraining intensief: 450-550 kcal/uur
- Zwemmen: 400-600 kcal/uur
- HIIT training: 500-700 kcal/uur

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
  "status": "complete" | "needs_clarification" | "no_data",
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
  "clarification_question": "Optionele vraag bij needs_clarification",
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

    def answer_question_with_stats(self, question: str, daily_stats: dict, weekly_stats: dict, recent_workouts: list = None, conversation_history: list = None) -> str:
        """
        Answer user questions using their daily and weekly statistics.
        
        Args:
            question: User's question
            daily_stats: Today's totals from get_daily_totals()
            weekly_stats: Weekly averages from get_weekly_averages()
            recent_workouts: List of workout dictionaries from last 7 days
            conversation_history: List of previous messages
        
        Returns:
            Natural language answer to the question
        """
        
        system_prompt = """Je bent een persoonlijke voedings- en fitness assistent die vragen beantwoordt op basis van iemands tracking data.

Je krijgt:
1. De vraag van de gebruiker
2. De dagwaardes van VANDAAG
3. De weekgemiddeldes van de AFGELOPEN 7 DAGEN
4. Een lijst met alle WORKOUTS van de afgelopen 7 dagen
5. De voorgaande conversatie (indien beschikbaar)

BELANGRIJKE INSTRUCTIES:
- Beantwoord de vraag direct en bondig
- Gebruik concrete cijfers uit de data
- Vergelijk dag vs week gemiddeldes waar relevant
- Gebruik de specifieke workout historie voor advies over planning/herstel
- Geef context: is dit goed/slecht? Hoe verhoudt het zich tot typische doelen?
- Geef praktische tips (bijv. meal planning, rustdagen) als dat past bij de vraag
- Gebruik emojis voor leesbaarheid
- Maximaal 3-4 zinnen tenzij complexe vraag
- Als er gerefereerd wordt naar eerdere berichten, gebruik de conversatie geschiedenis

VOORBEELDEN:

Vraag: "Hoe gaat het deze week?"
→ "Deze week zit je gemiddeld op 2150 kcal per dag (doel: 2000) en 145g protein 💪. Vandaag heb je 1850 kcal en 140g protein. Je zit consistent rond je doel - goed bezig!"

Vraag: "Haal ik genoeg protein?"
→ "Deze week gemiddeld 145g protein per dag, vandaag 140g. Voor spiergroei wordt 1.6-2.2g per kg lichaamsgewicht aanbevolen. Als je ~75kg bent zit je ruim goed! 💪"

Vraag: "Hoe moet ik mijn workouts plannen?"
→ "Je hebt de afgelopen 3 dagen hardgelopen en krachttraining gedaan (borst/triceps). Gezien de intensiteit zou ik vandaag een rustdag nemen of lichte cardio doen (wandelen/fietsen) voor herstel. 🧘‍♂️"

Blijf vriendelijk, motiverend en feitelijk."""

        # Format the stats data for the LLM
        stats_context = f"""**VANDAAG:**
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

        try:
            # Increased timeout for reasoning models
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip()
                return answer
            else:
                print(f"LLM Error (question): {response.status_code} - {response.text}")
                return "❌ Sorry, ik kon je vraag niet beantwoorden. Probeer het opnieuw."
                
        except Exception as e:
            print(f"Error answering question with LLM: {e}")
            return "❌ Er ging iets fout bij het beantwoorden van je vraag."

# Global instance
llm_service = LLMService()
