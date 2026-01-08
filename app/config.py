class BotConfig:
    # Model Configuratie
    MODEL_INTENT_CLASSIFICATION = "google/gemini-2.5-flash"  # Snel & gratis voor simpele classificatie
    MODEL_FOOD_PARSING = "google/gemini-3-pro-preview"  # Zeer accurate parsing met reasoning
    MODEL_QUESTION_ANSWERING = "google/gemini-3-pro-preview"  # Voor vragen met statistieken
    
    # User ID (tijdelijk - later meerdere users)
    DEFAULT_USER_ID = 1
    
    # Timezone
    TIMEZONE = "Europe/Amsterdam"
    
    # Conversation History
    MAX_HISTORY_MESSAGES = 10  # Aantal berichten in context (5 exchanges)
