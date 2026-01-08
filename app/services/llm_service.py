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

    def parse_food_and_workouts(self, text: str, conversation_history: list = None) -> dict:
        """
        Parse user text into meals and workouts using LLM.
        
        Args:
            text: Current user message
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
        
        Returns: {
            "status": "complete" | "needs_clarification" | "no_data",
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
3. Bepaal of je meer informatie nodig hebt voor een goede schatting
4. Houd context bij - als de gebruiker eerder een vraag heeft beantwoord, gebruik die info

Beslissingslogica:
- **COMPLETE**: Informatie is voldoende voor accurate schatting → bereken en geef korte samenvatting
- **NEEDS_CLARIFICATION**: Essentiële details ontbreken voor accurate schatting → stel slimme, specifieke vraag
  * Focus op: portiegroottes, bereidingswijze, type ingrediënten, intensiteit workout
  * Vraag alleen naar ESSENTIËLE info, geen perfectie
  * Je mag MEERDERE opvolgvragen stellen om tot een accurate schatting te komen
  * Voorbeeld: "Hoeveel rijst ongeveer? Een klein of groot bord?"
- **NO_DATA**: Geen maaltijd of workout te herkennen → vraag wat de gebruiker wil loggen

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
      "description": "volledige beschrijving",
      "calories": 650,
      "protein": 35.0,
      "carbs": 75.0,
      "fat": 18.0
    }
  ],
  "workouts": [
    {
      "description": "activiteit beschrijving",
      "duration_minutes": 60,
      "calories_burned": 280
    }
  ],
  "clarification_question": "Optionele vraag bij needs_clarification",
  "summary": "Optionele samenvatting bij complete (kort, ~1 zin per item)"
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
            'max_tokens': 2000
        }

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result['choices'][0]['message']['content']
                
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

# Global instance
llm_service = LLMService()
