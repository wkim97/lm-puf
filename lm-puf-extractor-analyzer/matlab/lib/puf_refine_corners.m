function pts_out = puf_refine_corners(pts0, img)
%PUF_REFINE_CORNERS  Snap 4 hand-placed corners to the sample edge.
%   PTS = PUF_REFINE_CORNERS(PTS0, IMG) takes 4 approximate corner positions
%   PTS0 (4 x 2, [x y], 0-based pixel coordinates) on the thermal frame IMG:
%     1. normalises IMG to 8 bit and smooths it (9 x 9 Gaussian),
%     2. Otsu-thresholds it (dark = sample) and keeps the largest blob,
%     3. moves every point to the nearest pixel of that blob's outer boundary,
%     4. refines each point to sub-pixel accuracy (puf_corner_subpix),
%     5. orders the result as top-left, top-right, bottom-right, bottom-left.
%
%   Mirrors iterative_refinement + order_points in samplematcher.py.
%   Requires Image Processing Toolbox.

img = double(img);
mn = min(img(:));
mx = max(img(:));
if mx > mn
    norm_u8 = uint8(floor((img - mn) * (255 / (mx - mn))));
else
    norm_u8 = zeros(size(img), 'uint8');
end

blur = uint8(round(imfilter(double(norm_u8), fspecial('gaussian', [9 9], 1.7), 'replicate')));
level = graythresh(blur);
mask = blur <= level * 255;                    % THRESH_BINARY_INV: the (cooler) sample is foreground

refined = double(pts0);
cc = bwconncomp(mask, 8);
if cc.NumObjects > 0
    areas = cellfun(@numel, cc.PixelIdxList);
    [~, k] = max(areas);
    largest = false(size(mask));
    largest(cc.PixelIdxList{k}) = true;
    B = bwboundaries(largest, 8, 'noholes');
    b = B{1};
    contour = [b(:, 2) - 1, b(:, 1) - 1];        % [x y], 0-based
    for i = 1:size(refined, 1)
        d = sum(bsxfun(@minus, contour, refined(i, :)).^2, 2);
        [~, j] = min(d);
        refined(i, :) = contour(j, :);
    end
end

refined = puf_corner_subpix(double(norm_u8), refined, 11, 40, 0.001);
pts_out = puf_order_points(refined);
end
