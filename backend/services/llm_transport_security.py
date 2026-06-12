import os


LLM_ALLOW_INSECURE_TLS_ENV = "HYPER_AI_ALLOW_INSECURE_LLM_TLS"


def llm_tls_verify_enabled() -> bool:
    value = os.getenv(LLM_ALLOW_INSECURE_TLS_ENV, "").strip().lower()
    return value not in {"1", "true", "yes", "on"}
