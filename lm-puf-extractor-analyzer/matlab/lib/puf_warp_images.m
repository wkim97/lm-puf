function out = puf_warp_images(images, pts, target_w, target_h, progress_fn)
%PUF_WARP_IMAGES  Perspective-correct every frame of a stack onto a fixed grid.
%   OUT = PUF_WARP_IMAGES(IMAGES, PTS, W, H, PROGRESS_FN)
%   IMAGES : N x H0 x W0 temperature stack.
%   PTS    : 4 x 2 sample corners [x y] in 0-based pixel coordinates, ordered
%            top-left, top-right, bottom-right, bottom-left.
%   W, H   : output size in pixels.
%   PROGRESS_FN (optional): function handle called as PROGRESS_FN(i, N) every
%            100 frames and on the last frame.
%   A projective transform is fitted that maps the 4 corners to the corners
%   of the W x H grid and applied to every frame with bilinear interpolation
%   (pixels mapped from outside the source are 0).  OUT is N x H x W single.
%
%   Mirrors warp_images_with_points in samplematcher.py.
%   Requires Image Processing Toolbox (fitgeotrans, imwarp).

if nargin < 5, progress_fn = []; end

moving = double(pts) + 1;                                   % 0-based -> MATLAB pixel centres
fixed = [0 0; target_w 0; target_w target_h; 0 target_h] + 1;
tform = fitgeotrans(moving, fixed, 'projective');
R = imref2d([target_h target_w]);

n = size(images, 1);
frames = permute(images, [2 3 1]);                          % H0 x W0 x N: contiguous frames
out = zeros(n, target_h, target_w, 'single');
for i = 1:n
    w = imwarp(frames(:, :, i), tform, 'linear', 'OutputView', R, 'FillValues', 0);
    out(i, :, :) = single(w);
    if ~isempty(progress_fn) && (mod(i - 1, 100) == 0 || i == n)
        progress_fn(i, n);
    end
end
end
