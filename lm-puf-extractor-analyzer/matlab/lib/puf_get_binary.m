function binary = puf_get_binary(img, min_c, max_c, block_size, C_val)
%PUF_GET_BINARY  Binarise a thermal ROI for one temperature window.
%   BINARY = PUF_GET_BINARY(IMG, MIN_C, MAX_C, BLOCKSIZE, C) clips the ROI to
%   the window [MIN_C, MAX_C] (pixels outside the window are set to MIN_C),
%   normalises it to [0,1], inverts it, converts to 8 bit and applies the
%   Gaussian adaptive threshold.  BINARY is uint8 with values 0 / 255.
%
%   Mirrors ModernThermalGUI.get_binary in execute.py.

if nargin < 4, block_size = 21; end
if nargin < 5, C_val = 2; end

cp = img;
cp(cp < min_c) = min_c;
cp(cp > max_c) = min_c;

mn = min(cp(:));
mx = max(cp(:));
if mx - mn == 0
    nrm = zeros(size(cp), 'like', cp);
else
    nrm = (cp - mn) / (mx - mn);
end

inv = 1 - nrm;
u8 = uint8(floor(inv * 255));          % numpy astype(uint8) truncates
binary = puf_adaptive_threshold(u8, block_size, C_val);
end
