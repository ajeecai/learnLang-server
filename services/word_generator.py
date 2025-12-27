import os
import json
import logging
import aiohttp
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def generate_words_service(
    payload: dict, username: str, session: aiohttp.ClientSession
):
    """
    处理生成单词或句子的业务逻辑。
    """
    logger.info(f"generate_words called by user: {username}")

    llm_api_url = os.getenv("LLM_API_URL")
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    http_proxy = os.getenv("HTTP_PROXY")

    if not llm_api_url or not llm_api_key:
        logger.error("LLM configuration missing")
        raise HTTPException(status_code=500, detail="Server configuration error")

    if isinstance(payload, list) and payload:
        words = [str(w) for w in payload]
        prompt = (
            f'Generate one short English sentence for each word in this list: "{" ".join(words)}", '
            "for practice. Return only the sentences in this json format: "
            '["sentence1", "sentence2", ...].'
        )
        upstream_payload = {
            "model": llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(os.getenv("MAX_TOKENS_ONCE", 4096)),
        }
        logger.info(f"Upstream payload: {upstream_payload}")
    else:
        if not isinstance(payload, dict):
            payload = {}
        prompt = """
        Generate a list of 10 unique IELTS vocabulary words, including their Chinese translations 
        (list all significant meanings with clear differences, up to 3) and phonetic transcription (in IPA). 
        Don't repeat words which have been used in the past 3 months.
        Return only in JSON format like
        [
          {"word": "word", "meaning": "简体中文1, 简体中文2, ...", "phonetic": "/IPA/"},
          ...
        ].
    """.strip()

        upstream_payload = {
            "model": payload.get("model", llm_model),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": payload.get(
                "max_tokens", int(os.getenv("MAX_TOKENS_ONCE", 4096))
            ),
        }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_api_key}",
    }

    try:
        async with session.post(
            llm_api_url, headers=headers, json=upstream_payload, proxy=http_proxy
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"LLM API Error: {response.status} - {error_text}")
                raise HTTPException(status_code=response.status, detail=error_text)
            data = await response.json()
            # logger.info(f"LLM response: {data}")
            try:
                return json.loads(data["choices"][0]["message"]["content"])
            except (KeyError, IndexError, TypeError):
                logger.error(f"Unexpected LLM response format: {data}")
                raise HTTPException(
                    status_code=500, detail="Invalid response format from LLM"
                )
    except aiohttp.ClientError as e:
        logger.error(f"LLM connection error: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to LLM")
