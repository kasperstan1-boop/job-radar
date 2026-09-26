import os
import logging
import json
from google import genai
from google.genai import types
from jobradar.prompt import get_prompt, get_system_instruction, response_schema

logger = logging.getLogger(__name__)

# Priorytetowa lista modeli zgodna z darmowymi limitami
PRIORITY = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

def get_models_to_try(client: genai.Client) -> list[str]:
    try:
        available = [
            m.name.replace("models/", "") for m in client.models.list()
            if m.supported_actions and "generateContent" in m.supported_actions
        ]
        
        models_to_try = [m for m in PRIORITY if m in available]
        
        if not models_to_try and available:
            models_to_try.append(available[0])
            
        return models_to_try
    except Exception as e:
        logger.error(f"Błąd podczas pobierania listy modeli: {e}")
        return ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]

def analyze_job(job: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.error("Brak GEMINI_API_KEY w środowisku.")
        raise ValueError("Brak klucza API Gemini.")

    client = genai.Client(api_key=api_key)
    models = get_models_to_try(client)
    
    if not models:
        logger.error("Brak dostępnych modeli Gemini obsługujących generateContent.")
        raise RuntimeError("Brak dostępnych modeli.")

    prompt_text = get_prompt(
        job_title=job.get("title", "Brak tytułu"),
        company=job.get("company", "Brak firmy"),
        raw_text=job.get("description", "")
    )
    
    config = types.GenerateContentConfig(
        system_instruction=get_system_instruction(),
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=0.1,
    )

    for model_name in models:
        try:
            logger.info(f"Próbuję użyć modelu: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=config,
            )
            
            try:
                result = json.loads(response.text)
                return {"result": result, "model": model_name}
            except json.JSONDecodeError:
                logger.error(f"Model {model_name} nie zwrócił poprawnego JSONa.")
                continue

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "resource_exhausted" in error_msg:
                logger.warning(f"Limit modelu {model_name} wyczerpany (429). Przełączam...")
                continue
            else:
                logger.error(f"Nieoczekiwany błąd modelu {model_name}: {e}")
                continue

    logger.error("Wszystkie modele z listy fallback zawiodły.")
    raise RuntimeError("Nie udało się przeanalizować oferty - wyczerpano wszystkie modele.")