import json
from pathlib import Path

from pytube import YouTube

act_net_captions_dir = Path("./activity-net-captions.v1-3")
train_json = act_net_captions_dir / "train.json"
val_1_json = act_net_captions_dir / "val_1.json"
val_2_json = act_net_captions_dir / "val_2.json"
failed_logs = act_net_captions_dir / "failed_downloads.csv"

download_dir = Path("./videos")
training_dir = download_dir / "training"
validation_dir = download_dir / "validation"

def get_video_id(video_key: str) -> str:
	if video_key[:2] == "v_":
		return video_key[2:]
	return video_key

def get_yt_url(video_id: str) -> str:
	return f"https://www.youtube.com/watch?v={video_id}"

def load_json(json_path: Path):
	with open(json_path, "r") as f:
		return json.load(f)

def write_failure(video_id: str, reason: str, failed_logs: Path):
	with open(failed_logs, "a") as f:
		f.write(f"{video_id},{reason}\n")

def download_video(video_id: str, output_dir: Path) -> bool:
	video_url = get_yt_url(video_id)

	yt = None
	try:
		yt = YouTube(video_url)

		# progressive videos contain both audio/video in same file
		filtered_videos = yt.streams.filter(progressive=True, file_extension="mp4")
	except:
		write_failure(video_id, "Video unavailable", failed_logs)
		return False

	if len(filtered_videos) <= 0:
		# add to failed videos log
		write_failure(video_id, "No viable videos", failed_logs)
		return False

	low_res_videos = filtered_videos.filter(fps="30fps", resolution="480p")
	if len(low_res_videos) > 0:
		try:
			low_res_videos.first().download(output_path=output_dir.as_posix(), filename=f"{video_id}.mp4", max_retries=5)
			return True
		except:
			pass
	
	try:
		filtered_videos.first().download(output_path=output_dir.as_posix(), filename=f"{video_id}.mp4", max_retries=5)
	except:
		write_failure(video_id, "Failed to download video", failed_logs)
		return False

	return True

if __name__ == "__main__":
	training = load_json(train_json)

	# the val_n.json files are the same, except val_1.json has more videos than val_2.json
	validation_1 = load_json(val_1_json)

	failed_videos = None

	if not failed_logs.exists():
		failed_logs.touch()

	with open(failed_logs, "r") as f:
		failed_videos = list(map(lambda line: line.split(",").pop(0), f.readlines()))

	if not training_dir.exists():
		training_dir.mkdir(parents=True)

	if not validation_dir.exists():
		validation_dir.mkdir(parents=True)

	downloaded_videos = {video.stem: True for video in training_dir.iterdir() }
	downloaded_videos.update({ video.stem: True for video in validation_dir.iterdir() })
	downloaded_videos.update({ video.strip(): True for video in failed_videos })

	i = 0
	training_count = len(training)

	for video in training:
		i += 1
		video_id = get_video_id(video)
		if video_id in downloaded_videos:
			print(f"Skipping already downloaded video {i}/{training_count}")
			continue

		# download, if False, update failed_videos
		if not download_video(video_id, training_dir):
			failed_videos.append(video_id)
			print(f"Download failed {i}/{training_count}")
		else:
			print(f"Downloaded training video {i}/{training_count}")

	i = 0
	validation_count = len(validation_1)

	for video in validation_1:
		i += 1
		video_id = get_video_id(video)
		if video_id in downloaded_videos:
			print(f"Skipping already downloaded video {i}/{validation_count}")
			continue

		if not download_video(video_id, validation_dir):
			failed_videos.append(video_id)
			print(f"Download failed {i}/{validation_count}")
		else:
			print(f"Downloaded validation video {i}/{validation_count}")

	print("Finished downloading all videos!")