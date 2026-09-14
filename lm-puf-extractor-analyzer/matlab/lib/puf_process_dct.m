function bits = puf_process_dct(binary, resize_size, use_sign, crop_spec)
%PUF_PROCESS_DCT  Turn a binary ROI into the 32 x 32 (1024-bit) response.
%   BITS = PUF_PROCESS_DCT(BINARY, RESIZE, USE_SIGN, CROPSPEC)
%     1. scales BINARY (0/255) to [0,1] and area-resizes it to RESIZE x RESIZE,
%     2. takes the orthonormal 2-D DCT (type II),
%     3. quantises the coefficients - sign (coef > 0) when USE_SIGN is true,
%        otherwise magnitude above the median of the non-DC magnitudes,
%     4. crops the 32 x 32 block given by CROPSPEC (default '2:33'),
%     5. XORs it with the fixed seed (puf_seed_rand2).
%   BITS is a 32 x 32 double matrix of 0/1.
%
%   Mirrors ModernThermalGUI.process_dct in execute.py.
%   Requires Image Processing Toolbox (dct2, imresize).

if nargin < 2 || isempty(resize_size), resize_size = 64; end
if nargin < 3 || isempty(use_sign),    use_sign = true;  end
if nargin < 4 || isempty(crop_spec),   crop_spec = '2:33'; end

img_f = double(binary) / 255;
img_r = puf_resize_area(img_f, resize_size, resize_size);    % exact area average (cv2 INTER_AREA)
dct_v = dct2(img_r);

if use_sign
    quant = double(dct_v > 0);
else
    % Skip sign quantisation: threshold |coef| at the median of the non-DC
    % magnitudes (reduces flips near zero while keeping the information).
    mag = abs(dct_v);
    mag_flat = mag;
    mag_flat(1, 1) = 0;                         % exclude the DC term
    positives = mag_flat(mag_flat > 0);
    if isempty(positives)
        thr = 0;
    else
        thr = median(positives);
    end
    quant = double(mag > thr);
end

[r0, r1, c0, c1] = puf_parse_dct_crop(crop_spec, size(quant, 1));
cropped = quant(r0:r1, c0:c1);

seed = puf_seed_rand2();
if ~isequal(size(seed), [32 32])
    seed = imresize(seed, [32 32], 'nearest');
end

bits = double(xor(cropped ~= 0, seed ~= 0));
end
