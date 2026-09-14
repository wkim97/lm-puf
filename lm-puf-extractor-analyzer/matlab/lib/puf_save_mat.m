function puf_save_mat(path, s)
%PUF_SAVE_MAT  Save the fields of struct S as variables of a MAT-file.
%   The file is written in the v7 format so that it can be read by the Python
%   tools (scipy.io.loadmat).  Variables larger than 2 GB cannot be stored in
%   v7; in that case the file is written as v7.3 (HDF5) with a warning - such
%   files are readable by MATLAB but not by scipy.io.loadmat.

try
    save(path, '-struct', 's', '-v7');
catch err
    warning('puf:saveMat', ['Could not save %s as MAT v7 (%s). Falling back to v7.3; ' ...
        'the file will not be readable by the Python tools.'], path, err.message);
    save(path, '-struct', 's', '-v7.3');
end
end
