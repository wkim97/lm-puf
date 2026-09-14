function map = puf_colormap(name, n)
%PUF_COLORMAP  Built-in MATLAB colormap by name (n x 3).
%   MAP = PUF_COLORMAP(NAME, N) returns N rows of the built-in colormap
%   function NAME ('jet', 'parula', 'hot', 'cool', 'gray', 'bone', 'copper',
%   'hsv', ...).  Any colormap function on the MATLAB path can be used.
%   The colormap only affects the on-screen preview and the *_thermal.png /
%   Reference_Thermal.png images, not the extracted response bits.

if nargin < 2, n = 256; end
name = lower(char(name));
if exist(name, 'file') ~= 2 && exist(name, 'builtin') ~= 5
    error('puf_colormap:unknown', 'Unknown colormap: %s', name);
end
map = feval(name, n);
end
