function rect = puf_order_points(pts)
%PUF_ORDER_POINTS  Order 4 corners as top-left, top-right, bottom-right, bottom-left.
%   RECT = PUF_ORDER_POINTS(PTS) with PTS 4 x 2 [x y].  The top-left corner has
%   the smallest x+y, the bottom-right the largest; the top-right has the
%   smallest y-x and the bottom-left the largest.

pts = double(pts);
rect = zeros(4, 2);
s = sum(pts, 2);
[~, i_min] = min(s);
[~, i_max] = max(s);
rect(1, :) = pts(i_min, :);
rect(3, :) = pts(i_max, :);
d = pts(:, 2) - pts(:, 1);
[~, j_min] = min(d);
[~, j_max] = max(d);
rect(2, :) = pts(j_min, :);
rect(4, :) = pts(j_max, :);
end
