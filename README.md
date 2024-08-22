# Sauron

Made for Windows.
Use simple cv2 template matching on last 10 screenshots. 
The only intresting part is having a config file so that you can use this on any window and get the exact screen size real-time, so it will work even when resizing.

This uses psutil to match a target window name to a PID. Which is easily usable for then for info. 

The other thing that was intresting is the scale in match tempalte. In this case we set a scale of the image (0.2, 1, 20) so that we can detect the object at any size.
This was especially relevant when trying to automate small UI buttons that can change size based on display device size. 

# OUTPUT EXAMPLE
--------------------------------------------------
Timestamp: 1724106594.3859274
Match found for template template.PNG at scale 0.87
Confidence: 0.9097
Position relative to window: (961, 574) to (1050, 619)
Absolute screen position: (2990, 610) to (3079, 655)
Change significance: 0.00%
--------------------------------------------------

![processed_1724106859 3954706](https://github.com/user-attachments/assets/907acc0f-14b2-4ba4-ada8-fcbf15e0d90c)

The idea of the frame differencing was that you could potentially trigger the matching based on the fact that the user is "active" or the difference between frames. 

You can add more processing steps: 
- Before grayscaling: get specific pixel color values.
- After grayscaling; Countours, etc
