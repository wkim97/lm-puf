function bits = puf_read_bits_xlsx(path)
%PUF_READ_BITS_XLSX  Read one response file written by execute.py / execute.m.
%   BITS = PUF_READ_BITS_XLSX(PATH) reads the numeric block of the first
%   sheet (header row excluded) and flattens it row by row into one column
%   vector - the same order as pandas' DataFrame.values.flatten().  With
%   several window columns the windows are therefore interleaved, exactly as
%   in hd_analyzer_min.py.

num = xlsread(path);
num(isnan(num)) = 0;
bits = reshape(num', [], 1);
bits = fix(bits);
end
