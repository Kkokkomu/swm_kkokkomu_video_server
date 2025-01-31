import os
from google.cloud import speech_v1p1beta1 as speech
import io
from moviepy.editor import ImageClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip, VideoFileClip
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

def create_subtitle_clips(video, sentences, words_info, chunk_size=5, fontsize=50, font='나눔명조', color='pink', max_chars_per_line=40):
    subtitle_clips = []
    
    for sentence_idx, (sentence_start_time, sentence_end_time) in enumerate(sentences):
        # Extract words for the current sentence
        sentence_words = [word_info for word_info in words_info if sentence_start_time <= word_info['end'] <= sentence_end_time]
        
        for i in range(0, len(sentence_words), chunk_size):
            chunk = sentence_words[i:i + chunk_size]
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

def concatenate_audios(audio_paths, output_path, silence_duration=0):
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=silence_duration)  # 무음
    for path in audio_paths:
        audio = AudioSegment.from_file(path)
        combined += audio + silence
    combined.export(output_path, format="wav")

def create_image_sequence_video(image_paths, durations, output_path, fps=24):
    clips = []
    for image_path, duration in zip(image_paths, durations):
        clip = ImageClip(image_path, duration=duration)
        clips.append(clip)
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(output_path, fps=fps, codec="libx264")

# 파일 경로
audio_paths = [
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/sentence_0.mp3',
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/sentence_1.mp3',
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/sentence_2.mp3'
]
image_paths = [
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/image/1.PNG',
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/image/2.PNG',
    '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/image/3.PNG'
]
combined_audio_path = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/combined_audio.wav'
video_output_path = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource/generated_video.mp4'
output_directory = '/Users/chung-guyeon/gouyeonch/swm/swm_kkokkomu_video_server/resource'
final_output_path = os.path.join(output_directory, 'final_output.mp4')

# FFMPEG 경로 설정
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/local/bin/ffmpeg"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/chung-guyeon/ssh/kkokkomu-mvp-stt-6b87122202e7.json"

# 여러 개의 오디오 파일을 하나로 결합
concatenate_audios(audio_paths, combined_audio_path)

# 각 오디오 파일의 길이를 가져옴 (딜레이 없이 계산)
durations = [AudioSegment.from_file(path).duration_seconds for path in audio_paths]
print("duration[0] : " + str(durations[0]))
print("duration[1] : " + str(durations[1]))
print("duration[2] : " + str(durations[2]))


# 이미지 시퀀스를 사용하여 비디오 생성
create_image_sequence_video(image_paths, durations, video_output_path)

# 생성된 비디오와 오디오 클립 불러오기
video = VideoFileClip(video_output_path)
audio = AudioFileClip(combined_audio_path)

video = video.set_audio(audio)

# 결합된 음성 파일로부터 단어 타이밍 정보 추출
words_info = transcribe_audio_with_timing(combined_audio_path)

# 각 문장의 시작과 끝 시간을 저장 (딜레이 없이)
sentence_times = [
    (0, durations[0]),  # sentence_0
    (durations[0], durations[0] + durations[1]),  # sentence_1
    (durations[0] + durations[1], sum(durations))  # sentence_2
]

# 단어 타이밍 정보로부터 자막 클립 생성
subtitle_clips = create_subtitle_clips(video, sentence_times, words_info)

# 비디오와 자막 합치기
final_video = CompositeVideoClip([video, *subtitle_clips])

# 결과물 저장
final_video.write_videofile(final_output_path, codec='libx264', audio_codec='aac', fps=24)

# 저장된 결과물의 자막 정보 출력
for word_info in words_info:
    print(f"Word: {word_info['word']}, Start: {word_info['start']}, End: {word_info['end']}")
