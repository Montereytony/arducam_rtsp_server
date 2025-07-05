# arducam_rtsp_server
This repository holds some code to broadcast cameras connected to my RaspberryPi 5. I have two arducams and a SiYi A8 that
I want to serve. To run them, I do: python multi_cam.py

All three of the following files are basically the same, the first multi_cam.py will just display my three cameras. The second file multi_cam_flipped.py, will flip vertically and horizontally my arducams because I mounted them upside down. The third file, multi_cam_no_distortion.py I am playing with the frames per second  and the resolution. The cams are very high resolution. I am bring them down to 961x720, but the image seems distorted so I was using this to test.
