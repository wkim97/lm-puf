function puf_save_colormapped_png(img, path, cmap, vmin, vmax)
%PUF_SAVE_COLORMAPPED_PNG  Save a scalar image as a colour-mapped PNG.
%   PUF_SAVE_COLORMAPPED_PNG(IMG, PATH, CMAP, VMIN, VMAX) maps IMG linearly
%   from [VMIN, VMAX] onto the rows of CMAP (values outside the range take
%   the first / last colour) and writes an RGB PNG - the same behaviour as
%   matplotlib.pyplot.imsave(path, img, cmap=..., vmin=..., vmax=...).

n = size(cmap, 1);
x = (double(img) - vmin) / (vmax - vmin);
idx = floor(x * n);
idx(idx >= n) = n - 1;
idx(idx < 0) = 0;
idx(isnan(idx)) = 0;
rgb = ind2rgb(idx + 1, cmap);
imwrite(rgb, path);
end
