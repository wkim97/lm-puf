function s = puf_format_float(x)
%PUF_FORMAT_FLOAT  Format a number the way Python prints a float (50 -> '50.0').
%   Used for folder / file names so that MATLAB and Python outputs are named
%   identically, e.g. 'sample_50.0_40.0_49.0_3.0.xlsx' and 'R1_40.0-43.0'.

s = sprintf('%.15g', double(x));
if isempty(regexp(s, '[.eEni]', 'once'))    % no decimal point, exponent, NaN or Inf
    s = [s '.0'];
end
end
