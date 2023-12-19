import base64
from io import BytesIO
import time
import uuid
from typing import Optional

from numpy import ndarray

from fastapi import APIRouter, HTTPException, UploadFile, status
from logger import logger
from pydantic import BaseModel, Field
from tts_app.model_manager import model_manager, tts_manager

from contants import ModelType

router = APIRouter()


def check_is_none(item) -> bool:
    # none -> True, not none -> False
    return (
        item is None
        or (isinstance(item, str) and str(item).isspace())
        or str(item) == ""
    )


class SpeakersResponse(BaseModel):
    speakers: dict[str, list]


@router.get(
    "/voice/speakers",
    status_code=status.HTTP_200_OK,
)
def speakers() -> SpeakersResponse:
    voice_speakers: dict[str, list] = model_manager.voice_speakers
    return SpeakersResponse(speakers=voice_speakers)


class BertVits2Request(BaseModel):
    text: str = Field(
        title="Text to synthesize.",
        min_length=1,
    )
    id: int = 0
    format: str = "wav"
    lang: str = "auto"
    length: float = 1.0
    length_zh: float = 0.0
    length_ja: float = 0.0
    length_en: float = 0.0
    noise: float = 0.667
    noisew: float = 0.8
    sdp_ratio: float = 0.2
    segment_size: int = 50
    use_streaming: bool = False
    emotion: Optional[int] = 0
    reference_audio: Optional[UploadFile] = None


class BertVits2Response(BaseModel):
    base64: str = Field(
        title="Base64 encoded audio.",
        examples=["PExABP9DnECtYeMICMCcB2w3dEOpuC7..."],
    )


@router.post(
    "/voice/bert-vits2",
)
def bert_vits2(req: BertVits2Request) -> BertVits2Response:
    text = req.text
    id = req.id
    format = req.format
    lang = req.lang
    length = req.length
    length_zh = req.length_zh
    length_ja = req.length_ja
    length_en = req.length_en
    noise = req.noise
    noisew = req.noisew
    sdp_ratio = req.sdp_ratio
    segment_size = req.segment_size
    use_streaming = req.use_streaming
    emotion = req.emotion
    reference_audio = req.reference_audio

    logger.info(
        f"[{ModelType.BERT_VITS2.value}] id:{id} format:{format} lang:{lang} length:{length} noise:{noise} noisew:{noisew} sdp_ratio:{sdp_ratio} segment_size:{segment_size}"
        f" length_zh:{length_zh} length_ja:{length_ja} length_en:{length_en}"
    )
    logger.info(f"[{ModelType.BERT_VITS2.value}] len:{len(text)} text：{text}")

    if check_is_none(text):
        logger.info(f"[{ModelType.BERT_VITS2.value}] text is empty")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is empty",
        )

    if check_is_none(id):
        logger.info(f"[{ModelType.BERT_VITS2.value}] speaker id is empty")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="speaker id is empty",
        )

    if id < 0 or id >= model_manager.bert_vits2_speakers_count:
        logger.info(
            f"[{ModelType.BERT_VITS2.value}] speaker id {id} does not exist"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"speaker id {id} does not exist",
        )

    if emotion and (emotion < 0 or emotion > 9):
        logger.info(
            f"[{ModelType.BERT_VITS2.value}] emotion {emotion} out of the range 0-9"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"emotion {emotion} out of the range 0-9",
        )

    # 校验模型是否支持输入的语言
    speaker_lang = model_manager.voice_speakers[ModelType.BERT_VITS2.value][
        id
    ].get("lang")
    if (
        lang not in ["auto", "mix"]
        and len(speaker_lang) != 1
        and lang not in speaker_lang
    ):
        logger.info(
            f'[{ModelType.BERT_VITS2.value}] lang "{lang}" is not in {speaker_lang}'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'lang "{lang}" is not in {speaker_lang}',
        )

    # 如果配置文件中设置了LANGUAGE_AUTOMATIC_DETECT则强制将speaker_lang设置为LANGUAGE_AUTOMATIC_DETECT
    # if current_app.config.get("LANGUAGE_AUTOMATIC_DETECT", []) != []:
    #     speaker_lang = current_app.config.get("LANGUAGE_AUTOMATIC_DETECT")

    if use_streaming and format.upper() != "MP3":
        format = "mp3"
        logger.warning("Streaming response only supports MP3 format.")

    fname = f"{str(uuid.uuid1())}.{format}"
    file_type = f"audio/{format}"
    state = {
        "text": text,
        "id": id,
        "format": format,
        "length": length,
        "length_zh": length_zh,
        "length_ja": length_ja,
        "length_en": length_en,
        "noise": noise,
        "noisew": noisew,
        "sdp_ratio": sdp_ratio,
        "segment_size": segment_size,
        "lang": lang,
        "speaker_lang": speaker_lang,
        "emotion": emotion,
        "reference_audio": reference_audio,
    }

    t1 = time.time()
    audio = tts_manager.bert_vits2_infer(state)
    t2 = time.time()
    logger.info(f"[{ModelType.BERT_VITS2.value}] finish in {(t2 - t1):.2f}s")
    base64EncodedAudio = __encode_wav(audio)
    return BertVits2Response(base64=base64EncodedAudio)

    # if current_app.config.get("SAVE_AUDIO", False):
    #     logger.debug(f"[{ModelType.BERT_VITS2.value}] {fname}")
    #     path = os.path.join(current_app.config.get("CACHE_PATH"), fname)
    #     save_audio(audio.getvalue(), path)

    # return send_file(
    #     path_or_file=audio, mimetype=file_type, download_name=fname
    # )

def __encode_wav(audio: BytesIO|ndarray):
    # BytesIO オブジェクトの場合
    if isinstance(audio, BytesIO):
        bytes_data = audio.getvalue()
    # ndarray の場合
    elif isinstance(audio, ndarray):
        bytes_data = audio.tobytes()
    else:
        raise TypeError("Unsupported audio type. Must be BytesIO or ndarray.")

    # Base64エンコード
    encoded_data = base64.b64encode(bytes_data)
    return encoded_data.decode('utf-8')