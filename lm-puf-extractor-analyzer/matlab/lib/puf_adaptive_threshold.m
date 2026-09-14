function bw = puf_adaptive_threshold(u8, block_size, C)
%PUF_ADAPTIVE_THRESHOLD  Gaussian-weighted adaptive threshold of an 8-bit image.
%   BW = PUF_ADAPTIVE_THRESHOLD(U8, BLOCKSIZE, C) returns a uint8 image that is
%   255 where U8 > localMean - C and 0 elsewhere.  The local mean is a
%   BLOCKSIZE x BLOCKSIZE Gaussian-weighted mean with replicated borders,
%   rounded to 8 bit, and C is applied as an integer bias (ceil(C)).  This is
%   the same definition as cv2.adaptiveThreshold(..., ADAPTIVE_THRESH_GAUSSIAN_C,
%   THRESH_BINARY, BLOCKSIZE, C) used by the Python extractor; the Gaussian
%   sigma follows OpenCV's kernel-size rule sigma = 0.3*((k-1)/2 - 1) + 0.8.
%
%   Requires Image Processing Toolbox (fspecial, imfilter).

u8 = uint8(u8);
block_size = double(block_size);
sigma = 0.3 * ((block_size - 1) * 0.5 - 1) + 0.8;
h = fspecial('gaussian', [block_size block_size], sigma);
local_mean = round(imfilter(double(u8), h, 'replicate', 'same'));
bw = uint8(double(u8) > (local_mean - ceil(C))) * 255;
end
