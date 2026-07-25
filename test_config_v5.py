from studio.config.loader import ProjectLoaderV5

project = ProjectLoaderV5("projects/project_v5.yaml").load()

print("Titre :", project.title)
print("GPX :", project.gpx.file)
print("Caméra :", project.camera.mode)
print("Distance :", project.camera.distance.minimum, "->", project.camera.distance.maximum)
print("Durée totale :", project.timeline.total_duration, "s")
print("Vidéo :", project.video.resolution, project.video.fps, "FPS")
