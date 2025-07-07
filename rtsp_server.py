#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

# Custom Media Factory to add logging for pipeline creation and state
class MyRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def do_create_element(self, url):
        # This method is called by the RTSP server to create the GStreamer pipeline
        # based on the launch string set by set_launch().
        # We override it to add error handling.
        try:
            # Gst.parse_launch is used to parse the pipeline string.
            # If the pipeline string is invalid, it will raise a GLib.Error.
            pipeline = Gst.parse_launch(self.get_launch())
            if pipeline:
                print(f"Successfully created pipeline for {url}: {self.get_launch()}")
            else:
                # This case should ideally be caught by the GLib.Error, but added for robustness.
                print(f"Failed to create pipeline for {url}. Pipeline string might be invalid or empty: {self.get_launch()}")
            return pipeline
        except GLib.Error as e:
            # Catch GStreamer parsing errors and print them
            print(f"ERROR: GStreamer pipeline creation failed for {url}: {e}. Pipeline string: {self.get_launch()}")
            return None

class RTSPServer:
    def __init__(self):
        # Initialize GStreamer. This must be called before using any GStreamer functions.
        Gst.init(None)

        # Create a new RTSP server instance
        self.server = GstRtspServer.RTSPServer()
        # Set the service port for the RTSP server. Changed to 8554 to avoid "Address already in use" error.
        self.server.set_property('service', '8554')
        # Set the server to listen on all available network interfaces (0.0.0.0)
        self.server.set_property('address', '0.0.0.0')

        # Get the mount points object from the server, where factories are added
        mount_points = self.server.get_mount_points()

        # --- Factory for Camera 0 (Original Camera) ---
        # Camera name for the first Arducam, as provided by you
        cam0_name = '/base/axi/pcie@1000120000/rp1/i2c@88000/imx477@1a'
        # Define the GStreamer pipeline for Camera 0.
        # Added 'queue' elements for better buffering and stability.
        # ADDED: videoflip method=rotate-180 for horizontal and vertical flip
        pipeline_cam0 = (
            f'libcamerasrc camera-name={cam0_name} ! '
            'videoconvert ! '
            'video/x-raw,format=I420 ! ' # Specify I420 format
            'videoscale ! '
            'video/x-raw,width=1280,height=720,framerate=30/1 ! ' # Specify desired resolution and framerate
            'videoflip video-direction=2 ! '  # Correct 180-degree rotation
            'queue ! ' # Add queue before encoding
            'x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! '
            'video/x-h264,profile=baseline ! '
            'queue ! ' # Add queue before RTP payloader
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_cam0 = MyRTSPMediaFactory() # Use our custom factory for better error logging
        factory_cam0.set_launch(pipeline_cam0)
        factory_cam0.set_shared(True) # Allows multiple clients to connect to the same stream
        mount_points.add_factory('/cam0', factory_cam0)
        print(f"Stream for Camera 0 configured at rtsp://0.0.0.0:8554/cam0")


        # --- Factory for Camera 1 (Second Arducam) ---
        # Camera name for the second Arducam, as provided by you
        cam1_name = '/base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a'
        # Define the GStreamer pipeline for Camera 1, similar to Camera 0
        # Added 'queue' elements for better buffering and stability.
        # ADDED: videoflip method=rotate-180 for horizontal and vertical flip
        pipeline_cam1 = (
            f'libcamerasrc camera-name={cam1_name} ! '
            'videoconvert ! '
            'video/x-raw,format=I420 ! ' # Specify I420 format
            'videoscale ! '
            'video/x-raw,width=1280,height=720,framerate=30/1 ! ' # Specify desired resolution and framerate
            'videoflip video-direction=2 ! '  # Correct 180-degree rotation
            'queue ! ' # Add queue before encoding
            'x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! '
            'video/x-h264,profile=baseline ! '
            'queue ! ' # Add queue before RTP payloader
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_cam1 = MyRTSPMediaFactory() # Use our custom factory
        factory_cam1.set_launch(pipeline_cam1)
        factory_cam1.set_shared(True)
        mount_points.add_factory('/cam1', factory_cam1)
        print(f"Stream for Camera 1 configured at rtsp://0.0.0.0:8554/cam1")


        # --- Factory for RTSP Restream ---
        # The URL of the existing RTSP stream to re-stream
        restream_url = 'rtsp://192.168.144.25:8554/main.264'
        # Define the GStreamer pipeline for re-streaming.
        # rtspsrc pulls the stream, rtph264depay depayloads it,
        # h264parse ensures correct H.264 stream parsing,
        # and rtph264pay re-payloads it for our server.
        # latency is added to help with buffering for the incoming stream.
        # Added 'queue' elements for better buffering and stability.
        pipeline_restream = (
            f'rtspsrc location={restream_url} latency=100 ! '
            'rtph264depay ! '
            'h264parse ! ' # Ensures the H.264 stream is properly parsed
            'queue ! ' # Add queue before RTP payloader
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_restream = MyRTSPMediaFactory() # Use our custom factory
        factory_restream.set_launch(pipeline_restream)
        factory_restream.set_shared(True)
        mount_points.add_factory('/restream', factory_restream)
        print(f"Restream of {restream_url} configured at rtsp://0.0.0.0:8554/restream")


        # Attach the server to the default GLib main context.
        # This makes the server active and ready to accept connections.
        self.server.attach(None)
        print("\nRTSP server started. Access streams from other devices using:")
        print("  rtsp://YOUR_PI_IP:8554/cam0")
        print("  rtsp://YOUR_PI_IP:8554/cam1")
        print("  rtsp://YOUR_PI_IP:8554/restream")

if __name__ == '__main__':
    server = RTSPServer()
    # Create a GLib main loop to keep the server running and processing events
    loop = GLib.MainLoop()
    try:
        loop.run() # Start the main loop
    except KeyboardInterrupt:
        # Handle Ctrl+C to gracefully stop the server
        print("\nStopping RTSP server.")
        loop.quit() # Exit the main loop
