import os
from google.cloud import speech_v1p1beta1 as speech
import io
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from pydub import AudioSegment

def transcribe_audio_with_timing(audio_path):
    client = speech.SpeechClient()

    with io.open(audio_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000,
        language_code="ko-KR",
        enable_word_time_offsets=True  # 타이밍 정보 활성화
    )

    response = client.recognize(config=config, audio=audio)

    words_info = []
    for result in response.results:
        alternative = result.alternatives[0]
        for word_info in alternative.words:
            word = word_info.word
            start_time = word_info.start_time.total_seconds()
            end_time = word_info.end_time.total_seconds()
            words_info.append({
                'word': word,
                'start': start_time,
                'end': end_time
            })
    
    return words_info

def wrap_text(text, max_chars_per_line):
    """주어진 텍스트를 최대 너비를 초과하지 않도록 줄바꿈합니다."""
    import textwrap
    return "\n".join(textwrap.wrap(text, width=max_chars_per_line))

def create_subtitle_clips(video, words_info, fontsize=50, font='나눔명조', color='black', max_chars_per_line=40):
    subtitle_clips = []
    chunk_size = 5

    for i in range(0, len(words_info), chunk_size):
        chunk = words_info[i:i + chunk_size]
        text = " ".join([word['word'] for word in chunk])
        start_time = chunk[0]['start']
        end_time = chunk[-1]['end']
        duration = end_time - start_time

        wrapped_text = wrap_text(text, max_chars_per_line)
        text_lines = wrapped_text.count('\n') + 1
        text_clip_height = text_lines * fontsize

        position_y = video.size[1] - 100 - (text_clip_height // 2)
        
        subtitle_clip = (TextClip(wrapped_text, fontsize=fontsize, font=font, color=color, size=(video.size[0] - 40, None), method='caption')
                         .set_position(("center", position_y))
                         .set_start(start_time)
                         .set_duration(duration))
        subtitle_clips.append(subtitle_clip)
    return subtitle_clips

def convert_mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

# 파일 경로
video_path = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/video.mp4'
audio_path = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/tts.mp3'
wav_path = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/audio.wav'
output_directory = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource'
output_path = os.path.join(output_directory, 'output.mp4')

# FFMPEG 경로 설정
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/local/bin/ffmpeg"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/chung-guyeon/ssh/kkokkomu-mvp-stt-6b87122202e7.json"

# mp3 파일을 wav 파일로 변환
convert_mp3_to_wav(audio_path, wav_path)

# 비디오와 오디오 클립 불러오기
video = VideoFileClip(video_path)
audio = AudioFileClip(audio_path)

video = video.set_audio(audio)

# 음성 파일로부터 단어 타이밍 정보 추출
words_info = transcribe_audio_with_timing(wav_path)

# 단어 타이밍 정보로부터 자막 클립 생성
subtitle_clips = create_subtitle_clips(video, words_info)

# 비디오와 자막 합치기
final_video = CompositeVideoClip([video, *subtitle_clips])

# 결과물 저장
final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)

# 저장된 결과물의 자막 정보 출력
for word_info in words_info:
    print(f"Word: {word_info['word']}, Start: {word_info['start']}, End: {word_info['end']}")
