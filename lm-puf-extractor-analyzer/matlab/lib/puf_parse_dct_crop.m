function [r0, r1, c0, c1] = puf_parse_dct_crop(crop_spec, n)
%PUF_PARSE_DCT_CROP  Parse the user-facing 1-based inclusive DCT crop range.
%   [R0, R1, C0, C1] = PUF_PARSE_DCT_CROP(SPEC, N) accepts
%       '2:33'       -> rows 2:33 and cols 2:33
%       '2:33,4:35'  -> rows 2:33 and cols 4:35
%       '2-33'       -> same as '2:33'
%   and returns 1-based inclusive MATLAB index bounds.  The selected area
%   must be exactly 32 x 32 and must fit inside an N x N DCT matrix.

spec = strtrim(char(crop_spec));
if isempty(spec)
    spec = '2:33';
end

parts = regexp(spec, '[,;]', 'split');
parts = strtrim(parts);
parts = parts(~cellfun('isempty', parts));

if numel(parts) == 1
    row_part = parts{1};
    col_part = parts{1};
elseif numel(parts) == 2
    row_part = parts{1};
    col_part = parts{2};
else
    error('puf:dctCrop', 'DCT Crop Range must be like 2:33 or 2:33,2:33');
end

[r0, r1] = parse_part(row_part, n);
[c0, c1] = parse_part(col_part, n);
end

function [s, e] = parse_part(part, n)
tok = regexp(strtrim(part), '^(\d+)\s*[:-]\s*(\d+)$', 'tokens', 'once');
if isempty(tok)
    error('puf:dctCrop', 'DCT Crop Range must be like 2:33 or 2:33,2:33');
end
s = str2double(tok{1});
e = str2double(tok{2});
if s < 1 || e < s
    error('puf:dctCrop', 'DCT Crop Range must use 1-based increasing indices');
end
if (e - s + 1) ~= 32
    error('puf:dctCrop', 'DCT Crop Range must select exactly 32 values, e.g. 2:33');
end
if e > n
    error('puf:dctCrop', 'DCT Crop Range %d:%d exceeds DCT size %d', s, e, n);
end
end
