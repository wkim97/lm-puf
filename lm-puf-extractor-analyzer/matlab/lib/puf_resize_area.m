function out = puf_resize_area(img, out_rows, out_cols)
%PUF_RESIZE_AREA  Down-scale an image by exact pixel-area averaging.
%   OUT = PUF_RESIZE_AREA(IMG, ROWS, COLS) gives every output pixel the mean
%   of the input area it covers, weighting partially covered input pixels by
%   their overlap fraction (the definition of cv2.resize INTER_AREA when
%   shrinking).  Implemented as OUT = Wy * IMG * Wx' with 1-D overlap-weight
%   matrices.  When an axis is enlarged instead, bilinear interpolation is
%   used for that axis.
%
%   imresize(..., 'box') is not used because its box kernel is evaluated at
%   pixel centres, which gives different weights for partially covered pixels.

img = double(img);
Wy = weights(size(img, 1), out_rows);
Wx = weights(size(img, 2), out_cols);
out = Wy * img * Wx';
end

function W = weights(src_len, dst_len)
if dst_len >= src_len
    % enlarging: bilinear (pixel-centre aligned), as cv2 falls back to for INTER_AREA
    W = zeros(dst_len, src_len);
    scale = src_len / dst_len;
    for d = 1:dst_len
        s = (d - 0.5) * scale - 0.5;          % 0-based source coordinate of the output centre
        s = min(max(s, 0), src_len - 1);
        i0 = floor(s);
        f = s - i0;
        i1 = min(i0 + 1, src_len - 1);
        W(d, i0 + 1) = W(d, i0 + 1) + (1 - f);
        W(d, i1 + 1) = W(d, i1 + 1) + f;
    end
    return
end
scale = src_len / dst_len;
W = zeros(dst_len, src_len);
for d = 1:dst_len
    s0 = (d - 1) * scale;
    s1 = s0 + scale;
    i0 = floor(s0);
    i1 = min(ceil(s1), src_len);
    for i = i0:i1 - 1
        overlap = min(s1, i + 1) - max(s0, i);
        if overlap > 0
            W(d, i + 1) = overlap / scale;
        end
    end
end
end
