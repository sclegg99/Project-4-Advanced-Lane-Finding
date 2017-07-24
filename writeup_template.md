# Project 4--Advanced Lane Finding

# *Rubic Points*
## The goals / steps of this project are the following:
* Compute the camera calibration matrix and distortion coefficients given a set of chessboard images.
* Apply a distortion correction to raw images.
* Use color transforms, gradients, etc., to create a thresholded binary image.
* Apply a perspective transform to rectify binary image ("birds-eye view").
* Detect lane pixels and fit to find the lane boundary.
* Determine the curvature of the lane and vehicle position with respect to center.
* Warp the detected lane boundaries back onto the original image.
* Output visual display of the lane boundaries and numerical estimation of lane curvature and vehicle position.

## Camera Calibration
Camera calibration was performed using the python script [*CameraCalibration.py*](./CameraCalibration.py). The routine performed the following:
1. Read a chessboard image.
2. Convert the image from color to gray scale.
3. Identify the chessboard corner locations using the OpenCV routine findChessboardCorners.
4. Further refine the estimate of the corner location using the OpenCV routine cornerSubPix.
5. Append the corner locations to a list
6. Repeat steps 1-5 until all the chessboard images have been processed.
7. The camera calibartion matrix and distortion coefficients are then estimated using the OpenCV routine cv2.calibrateCamera.
8. The accuracy of the calculated camera calibration is then estimated by reprojecting the coner points onto the chessboard.
9. Finally the calibration matrix and distoriton coefficients are saved to a pickle file.
A totaly of twenty chessboard images were provided to the camera calibration.  Of those twenty files, five were rejected for processing due to incompatatible image sizes.  The final estimated camera calibration values were:

Camera matrix is

| | | |
| :---: | :---: | :---: |
| 1158.7734939444706 |    0.0 | 669.6411388407582 |
|    0.0 | 1154.0749356989813 | 388.0784814554919 |
|    0.0 |    0.0 |   1.0 |


Lens distortion coefficients are

| Coefficient | Value |
| :---: | :---: |
| r1 |-0.2567800687154464 |
| r2 | 0.04339333102260943 |
| r3 |-0.1150366506303131 |
| t1 |-0.0006876303026921493 |
| t1 | 0.00012574538927438055 |

Reprojection estimates are

|  |  |
| :---: | :---: |
| Mean | 0.77856300011631 |
| Standard Deviation | 0.2915895232436049 |

A montage of the original chessboard images and their images after undistortion is show in Figure 1.

![Figure 1](./Figures/checkboard_montage.png?test=raw)

Figure 1: Montage of original and undistorted chessboard images.

The physical size of the chessboard squares was not provided for this exercise.  Hence the estimated focal lengths are not the actual focal length but are only relative to the assumed chessboard size of 1 unit by 1 unit.

## Lane Finding Pipeline
The first step was to initialize the camera calibration data by reading for the pickle file which conatained the camera calibration matrix and distortion coeficients.  The the pipeline was executed as follows:
1. A frame of the project video was read.
2. The frame image was undistorted using the camera calibration data and the OpenCV routine undistort.
3. The undistorted image was converted to a gray scale.  Several gray scale conversions were considered and the optimal choice was to seperate the image into its YCrCb channels and select on the Y channel for additional processing. (See line 173.)
4. The Sobel X and Y gradients were calculated over the extent of the gray scale image with a kernel size of 9 and thresholds of (50, 200). (See lines 182 through 187.)
5. The X and Y gradients were added weighting the X gradient by 2 and the Y gradient by 1. (See line 192.)
6. Then a morphological close was performed on the weighted binary image with a default kernal size of 3.  The purpose of this step was to eliminate spurious pixels and while connecting neighboring pixels. (See lines 203 and 204.)
7. This closed image was then warped into a birds-eye view using the OpenCV warpPerspective routine. (See line 207.)
8. The warped image was then masked such that only the areas around the lane were visable.  The mask was dynamically adjusted to follow the radius of curvature of the lanes. (See lines 212 through 218.)
9. The masked image was then processed to by the routine supplied by Udacity to estimage the curve that represents the left and right lanes.  The Udacity routine was modified to fit a 2nd order polynoial with forced the slope of the curve representing the lane to 0 at the bottom edge of the image.  It was reasoned that the lane line must be parallel to the direction of car travel hence the slope (dx/dy) is zero at the bottom of the warped video image. (See find_the_lanes -- lines 237 through 398.)
10.  The [radius of curvature](https://en.wikipedia.org/wiki/Radius_of_curvature) was then calcuated for the left and right lane line curves.
11. A polyfill was generated representing the area between the left line curve and right line curve. (See line 231.)
12. The polyfill was then unwarped and distorted to match the original frame conditions (See lines 232 and 545.)
13. This unwarped and distorted image was then superimposed on the original frame and displayed and saved (See lines 575 and 576.)
14. Steps 1 through 13 were repeated until all the video frames were read and processed.

### 1. Distortion-corrected image.

Step 2 is illustrated in Figure 2 where a test image was undistorted using the previously calculated and stored camera calibration data.

![Figure 2](./Figures/StraightLaneUndistorted.png?test=raw)

Figure 2: Undistorted image. The sample straight lines image was used to illustrate this step

### 2. Steps 4 through 6 used color transforms, gradients, morphologic close and masking to create a thresholded binary image.

The image was mapped into YCrCb color space and the Y channel was then processed with Sobel X and Y gradients.  The YCrCb space was chosen because this color mapping seemed to be less senstivite to changes in the background color of the road surface.  I also explored the use of contrast limited adaptive histogram equalization (CLAHE) to improve the gradient selection.  However, CLAHE did not improve the line selection.  Therefore, CLAHE was not used.  Examples of the X and Y gradients are shown in Figures 3 and 4.

![Figure 3](./Figures/SobelXNoCLAHE.png?test=raw)

Figure 3: Sobel X gradients applied to sample images. Kernel was 9 and thresholds were (50, 200)

![Figure 4](./Figures/SobelYNoCLAHE.png?test=raw)

Figure 4: Sobel Y gradients applied to sample images. Kernel was 9 and thresholds were (50, 200)

The reult of combining the X and Y gradients and mophologic close are illustrated in Figure 5.

![Figure 5](./Figures/ExampleBinaryImage.png?test=raw)

Figure 5: Illustration of operating on the frame (a) to obtain the sum of the gradients (b) and then the result of the mophologic close (c).

### 3. Perspective transform to obtain a birds-eye view.

A perspective transform was performed to warp the image into a birds-eye view.  The warping was performed using the OpenCV function warpPerspective which is invoked on line 207.  The straight line images were used to define the source (src) and destination (dst) points.
```
src = np.float32([[972.296, 613.839],
                      [697.561, 442.204],
                      [626.414, 442.204],
                      [372.814, 613.839]])

offset_x = (image_shape[0]-137)/2
offset_y = image_shape[1]-300

dst = np.float32([[116+offset_x,286+offset_y],
                      [114+offset_x,  0+offset_y],
                      [  2+offset_x,  0+offset_y],
                      [  0+offset_x,286+offset_y]])
```

This resulted in the following source and destination points:

| Source        | Destination   | 
|:-------------:|:-------------:| 
| 585, 460      | 320, 0        | 
| 203, 720      | 320, 720      |
| 1127, 720     | 960, 720      |
| 695, 460      | 960, 0        |

I verified that my perspective transform was working as expected by drawing the `src` and `dst` points onto a test image and its warped counterpart to verify that the lines appear parallel in the warped image.

![alt text][image4]

### 4. Describe how (and identify where in your code) you identified lane-line pixels and fit their positions with a polynomial?

Then I did some other stuff and fit my lane lines with a 2nd order polynomial kinda like this:

![alt text][image5]

### 5. Describe how (and identify where in your code) you calculated the radius of curvature of the lane and the position of the vehicle with respect to center.

I did this in lines # through # in my code in `my_other_file.py`

### 6. Provide an example image of your result plotted back down onto the road such that the lane area is identified clearly.

I implemented this step in lines # through # in my code in `yet_another_file.py` in the function `map_lane()`.  Here is an example of my result on a test image:

![alt text][image6]

---

## Pipeline (video)

### 1. Provide a link to your final video output.  Your pipeline should perform reasonably well on the entire project video (wobbly lines are ok but no catastrophic failures that would cause the car to drive off the road!).

Here's a [link to my video result](./project_video.mp4)

---

## Discussion

### 1. Briefly discuss any problems / issues you faced in your implementation of this project.  Where will your pipeline likely fail?  What could you do to make it more robust?

Here I'll talk about the approach I took, what techniques I used, what worked and why, where the pipeline might fail and how I might improve it if I were going to pursue this project further.  
