import base64
from collections.abc import Callable
from typing import Literal

from google import genai
from pydantic import BaseModel

from prompts import ANALYSIS_PROMPT, transcription_prompt


MODEL_NAME = "gemini-3.6-flash"


class UncertainExcerpt(BaseModel):
    excerpt: str
    alternatives: list[str]
    confidence: Literal["baixa", "media"]
    context: str


class TranscriptionResult(BaseModel):
    transcription: str
    revised_transcription: str
    corrections: str
    uncertain_excerpts: list[UncertainExcerpt]


class EvidenceItem(BaseModel):
    value: str
    context: str
    evidence: str


class PersonProfile(BaseModel):
    name: str
    role: str
    information: list[str]
    evidence: str


class DocumentRelationship(BaseModel):
    source_person: str
    relationship: str
    target_person: str
    status: Literal["confirmada", "hipotese"]
    evidence: str
    rationale: str


class GenealogyResult(BaseModel):
    document_type: str
    main_event: str
    people: list[PersonProfile]
    relationships: list[DocumentRelationship]
    dates: list[EvidenceItem]
    localities: list[EvidenceItem]
    other_information: list[EvidenceItem]
    contextualization: str


def _client():
    """Create the client on demand so importing the app does not require a key."""
    return genai.Client()


def _stream_interaction(
    client,
    request: dict,
    on_progress: Callable[[float, str], None] | None,
) -> str:
    """Collect streamed text and report approximate progress from API events."""
    if on_progress:
        on_progress(0.05, "Enviando solicitação ao Gemini...")

    stream = client.interactions.create(stream=True, **request)
    text_parts = []
    output_length = 0
    current_step = ""

    for event in stream:
        if event.event_type == "interaction.created":
            if on_progress:
                on_progress(0.2, "Gemini recebeu a solicitação; analisando...")
        elif event.event_type == "step.start":
            current_step = event.step.type
            if current_step == "thought" and on_progress:
                on_progress(0.3, "Analisando o documento...")
            elif current_step == "model_output" and on_progress:
                on_progress(0.55, "Preparando a resposta...")
        elif event.event_type == "step.delta":
            if event.delta.type == "text":
                text_parts.append(event.delta.text)
                output_length += len(event.delta.text)
                if current_step == "model_output" and on_progress:
                    progress = min(0.92, 0.55 + output_length / 10000 * 0.37)
                    on_progress(progress, "Gerando a resposta...")
        elif event.event_type == "interaction.completed" and on_progress:
            on_progress(0.98, "Finalizando...")
        elif event.event_type == "error":
            error = getattr(event, "error", None)
            code = getattr(error, "code", "")
            message = getattr(error, "message", "Erro durante a análise.")
            raise RuntimeError(f"{code}: {message}".strip(": "))

    if on_progress:
        on_progress(1.0, "Análise concluída.")
    return "".join(text_parts)


def image_analise(
    image_bytes: bytes,
    mime_type: str,
    on_progress: Callable[[float, str], None] | None = None,
) -> TranscriptionResult:
    if not image_bytes:
        raise ValueError("A imagem enviada está vazia.")

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    with _client() as client:
        request = {
            "model": MODEL_NAME,
            "input": [
                {"type": "text", "text": transcription_prompt},
                {"type": "image", "data": image_b64, "mime_type": mime_type},
            ],
            "response_format": [
                {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": TranscriptionResult.model_json_schema(),
                }
            ],
        }
        output_text = _stream_interaction(client, request, on_progress)

    if not output_text:
        raise ValueError("O Gemini retornou uma resposta vazia.")
    return TranscriptionResult.model_validate_json(output_text)


def analyze_transcription(
    transcription: str,
    on_progress: Callable[[float, str], None] | None = None,
) -> GenealogyResult:
    if not transcription.strip():
        raise ValueError("A transcrição está vazia; não é possível analisá-la.")

    request = {
        "model": MODEL_NAME,
        "input": f"{ANALYSIS_PROMPT}\n\nTRANSCRIÇÃO:\n{transcription}",
        "response_format": [
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": GenealogyResult.model_json_schema(),
            }
        ],
    }
    with _client() as client:
        output_text = _stream_interaction(client, request, on_progress)
    if not output_text:
        raise ValueError("O Gemini retornou uma análise vazia.")
    return GenealogyResult.model_validate_json(output_text)
