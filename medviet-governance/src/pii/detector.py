# src/pii/detector.py
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

VI_LANGUAGE = "vi"
_VI_MODEL_CANDIDATES = ("vi_spacy_model", "vi_core_news_lg")


def _resolve_vi_model(cache_dir: Path) -> str:
    import spacy
    for name in _VI_MODEL_CANDIDATES:
        try:
            spacy.load(name)
            return name
        except OSError:
            continue
    # fallback: blank vi model serialised to disk so presidio can load it by path
    blank_path = cache_dir / ".spacy_models" / "vi_blank"
    if not blank_path.exists():
        blank_path.parent.mkdir(parents=True, exist_ok=True)
        spacy.blank("vi").to_disk(blank_path)
    return str(blank_path)


def build_vietnamese_analyzer(cache_dir: Path | None = None) -> AnalyzerEngine:
    cache_dir = cache_dir or Path.cwd()

    cccd_pattern = Pattern(name="cccd_pattern", regex=r"\b\d{12}\b", score=0.9)
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        supported_language=VI_LANGUAGE,
        patterns=[cccd_pattern],
        context=["cccd", "căn cước", "chứng minh", "cmnd"],
    )

    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(name="vn_phone", regex=r"\b0[35789]\d{8}\b", score=0.85)],
        context=["điện thoại", "sdt", "phone", "liên hệ"],
    )

    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(
            name="email_pattern",
            regex=r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
            score=0.9,
        )],
        context=["email", "mail", "gmail"],
    )

    # Regex-based VN person recognizer — matches Capitalised Vietnamese words (with diacritics)
    person_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(
            name="vn_person_latin",
            regex=(
                r"\b[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
                r"[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*"
                r"(?:\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
                r"a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+){0,3}\b"
            ),
            score=0.65,
        )],
    )

    model_name = _resolve_vi_model(cache_dir)
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": VI_LANGUAGE, "model_name": model_name}],
    })
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[VI_LANGUAGE])
    for rec in (cccd_recognizer, phone_recognizer, email_recognizer, person_recognizer):
        analyzer.registry.add_recognizer(rec)

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    return analyzer.analyze(
        text=text,
        language=VI_LANGUAGE,
        entities=["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"],
    )
