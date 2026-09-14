function images = puf_load_images(mat_path, prefer)
%PUF_LOAD_IMAGES  Load a temperature stack from a MAT-file.
%   IMAGES = PUF_LOAD_IMAGES(PATH) returns the N x H x W stack stored under
%   the variable 'temperature_frames' (Count2Temp output) or 'images'
%   (samplematcher output), whichever is present.
%   IMAGES = PUF_LOAD_IMAGES(PATH, 'images') looks for 'images' first
%   (the preference of execute.py).

if nargin < 2, prefer = 'temperature_frames'; end
if strcmp(prefer, 'images')
    order = {'images', 'temperature_frames'};
else
    order = {'temperature_frames', 'images'};
end

data = load(mat_path);
images = [];
for k = 1:numel(order)
    if isfield(data, order{k})
        images = data.(order{k});
        return
    end
end
[~, name, ext] = fileparts(mat_path);
error('puf:load', 'No valid image data found in %s%s.', name, ext);
end
