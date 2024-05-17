import logging
import aiohttp
import time
from collections.abc import AsyncIterable

from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([FasterASRSTT(hass, config_entry)])


class FasterASRSTT(stt.SpeechToTextEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        server: str = config_entry.data["server"]

        if server.endswith('/'):
            self.address = f"{server}api"
        else:
            self.address = f"{server}/api"
        self.model : str = config_entry.data["model"]
        self._attr_name = f"Fun Asr server: ({server})"
        self._attr_unique_id = f"{config_entry.entry_id[:7]}-fun-asr"

    @property
    def supported_languages(self) -> list[str]:
        return ['zh']

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        return [stt.AudioChannels.CHANNEL_MONO]

    def genHeader(self, sampleRate, bitsPerSample, channels, samples):
        datasize = samples * channels * bitsPerSample // 8
        o = bytes("RIFF",'ascii')                                               # (4byte) Marks file as RIFF
        o += (datasize + 36).to_bytes(4,'little')                               # (4byte) File size in bytes excluding this and RIFF marker
        o += bytes("WAVE",'ascii')                                              # (4byte) File type
        o += bytes("fmt ",'ascii')                                              # (4byte) Format Chunk Marker
        o += (16).to_bytes(4,'little')                                          # (4byte) Length of above format data
        o += (1).to_bytes(2,'little')                                           # (2byte) Format type (1 - PCM)
        o += (channels).to_bytes(2,'little')                                    # (2byte)
        o += (sampleRate).to_bytes(4,'little')                                  # (4byte)
        o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
        o += (channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
        o += (bitsPerSample).to_bytes(2,'little')                               # (2byte)
        o += bytes("data",'ascii')                                              # (4byte) Data Chunk Marker
        o += (datasize).to_bytes(4,'little')                                    # (4byte) Data size in bytes
        return o

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        _LOGGER.debug("process_audio_stream start")

        audio = b""
        async for chunk in stream:
            audio += chunk

        _LOGGER.debug(f"process_audio_stream transcribe: {len(audio)} bytes")

        wav_header = self.genHeader(stt.AudioSampleRates.SAMPLERATE_16000, stt.AudioBitRates.BITRATE_16, stt.AudioChannels.CHANNEL_MONO, len(audio))
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file',wav_header+audio,
                filename= f'{time.time()}.wav',
                content_type='audio/wav')
                data.add_field('language', 'zh')
                data.add_field('model', 'base')
                data.add_field('response_format', 'json')

                async with session.post(self.address, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        _LOGGER.debug(f"process_audio_stream end: {result}")
                        if result['code'] == 0 :
                            d = result['data']
                            if (len(d) > 0):
                                return stt.SpeechResult(d[0]['text'], stt.SpeechResultState.SUCCESS)
                            else:
                                _LOGGER.info("未识别要语音信息")
                                return stt.SpeechResult('', stt.SpeechResultState.SUCCESS)
                        else:
                            return stt.SpeechResult(result['msg'], stt.SpeechResultState.SUCCESS)
        except Exception as err:
            _LOGGER.exception("Error processing audio stream: %s", err)
            return stt.SpeechResult('识别出现异常，请检查配置是否正确', stt.SpeechResultState.SUCCESS)

        return stt.SpeechResult(None, stt.SpeechResultState.ERROR)





