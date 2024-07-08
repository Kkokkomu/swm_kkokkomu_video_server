import os
import speech_recognition as sr
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from pydub import AudioSegment, silence
import textwrap

def transcribe_audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)
    with audio_file as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language='ko-KR')  # 한국어 인식
        return text
    except sr.UnknownValueError:
        print("Google Web Speech API could not understand the audio")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Web Speech API; {e}")
        return ""

# 자막을 10글자씩 나누기
def split_text_to_subtitles(text, max_length=10):
    lines = text.split('\n')
    print(lines)
    subtitles = []
    for line in lines:
        wrapped_lines = textwrap.wrap(line, max_length)
        subtitles.extend(wrapped_lines)
    return subtitles

# 무음 구간에 자막 타이밍 할당
def assign_subtitle_timing(subtitles, silences, video_duration):
    subtitle_timed = []
    num_silences = len(silences)
    print("num_silences : " + str(num_silences))
    num_subtitles = len(subtitles)
    print("num_subtitles : " + str(num_subtitles))

    for i, subtitle in enumerate(subtitles):
        if i < num_silences - 1:
            start_time = silences[i][1]
            end_time = silences[i + 1][0]
        else:
            start_time = silences[-1][1] if num_silences > 0 else 0
            end_time = min(start_time + 2, video_duration)  # 마지막 자막은 2초 지속, 비디오 길이 내로 제한
        subtitle_timed.append({
            'text': subtitle,
            'start': start_time,
            'end': end_time
        })
    return subtitle_timed

# 자막 클립 생성
def create_subtitle_clip(subtitle, fontsize=50, font='나눔명조', color='white'):
    text = subtitle['text']
    start_time = subtitle['start']
    end_time = subtitle['end']
    duration = end_time - start_time

    subtitle_clip = (TextClip(text, fontsize=fontsize, font=font, color=color)
                     .set_position(("center"))
                     .set_start(start_time)
                     .set_duration(duration))
    return subtitle_clip

def convert_mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

# 파일 경로
video_path = '/Users/chung-guyeon/gouyeonch/swm/edit_video/video.mp4'
audio_path = '/Users/chung-guyeon/gouyeonch/swm/edit_video/tts.mp3'
wav_path = '/Users/chung-guyeon/gouyeonch/swm/edit_video/audio.wav'
output_directory = '/Users/chung-guyeon/gouyeonch/swm/edit_video'
output_path = os.path.join(output_directory, 'output.mp4')

# FFMPEG 경로 설정
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/local/bin/ffmpeg"

# mp3 파일을 wav 파일로 변환
convert_mp3_to_wav(audio_path, wav_path)

# 비디오와 오디오 클립 불러오기
video = VideoFileClip(video_path)
audio = AudioFileClip(wav_path)

# 비디오에 오디오 추가
video = video.set_audio(audio)

# 비디오 길이 가져오기
video_duration = video.duration
print("video duration : " + str(video_duration))

# 오디오 파일을 pydub로 로드
audio_segment = AudioSegment.from_file(wav_path)

# 오디오에서 무음 구간 찾기
silence_threshold = -40  # dBFS
min_silence_len = 500  # milliseconds
silences = silence.detect_silence(audio_segment, min_silence_len, silence_threshold)
silences = [(start / 1000, stop / 1000) for start, stop in silences]
print("silences : " + str(silences))

# 오디오 파일로부터 텍스트 추출
transcribed_text = transcribe_audio_to_text(wav_path)
print(transcribed_text)

# 추출한 텍스트를 자막으로 나누기
split_subtitles = split_text_to_subtitles(transcribed_text)

# 무음 구간에 자막 타이밍 할당
timed_subtitles = assign_subtitle_timing(split_subtitles, silences, video_duration)

# 자막 클립 생성
subtitle_clips = [create_subtitle_clip(sub) for sub in timed_subtitles]

# test TextClip 객체의 주요 속성 출력
print(f"Text: {test.txt}")
print(f"Font size: {test.size}")
print(f"Position: {test.pos}")
print(f"Start time: {test.start}")
print(f"Duration: {test.duration}")
print(f"Color: {test.color}")

# 비디오와 자막 합치기
final_video = CompositeVideoClip([video, *subtitle_clips])
# final_video = CompositeVideoClip([video, test])


# 결과물 저장
final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)

# 저장된 결과물의 자막 정보 출력
for sub in timed_subtitles:
    print(f"Text: {sub['text']}, Start: {sub['start']}, End: {sub['end']}")
