function pts = puf_corner_subpix(img, pts, win, max_iter, eps_val)
%PUF_CORNER_SUBPIX  Iterative sub-pixel corner refinement.
%   PTS = PUF_CORNER_SUBPIX(IMG, PTS, WIN, MAXITER, EPS) refines each corner
%   in PTS (N x 2, [x y], 0-based) on the grey image IMG by solving, in a
%   (2*WIN+1)^2 Gaussian-weighted window, the least-squares condition that the
%   image gradient at every window pixel is orthogonal to the vector from that
%   pixel to the corner (the classic Foerstner / cv2.cornerSubPix iteration).
%   Iteration stops after MAXITER steps or when the update is below EPS.
%   A point that drifts more than WIN pixels is reset to its initial position.

if nargin < 3 || isempty(win),      win = 11;    end
if nargin < 4 || isempty(max_iter), max_iter = 40; end
if nargin < 5 || isempty(eps_val),  eps_val = 0.001; end

[H, W] = size(img);
[jj, ii] = meshgrid(-win:win, -win:win);              % jj = x offsets, ii = y offsets
mask = exp(-((jj / win).^2 + (ii / win).^2));
[pjj, pii] = meshgrid(-(win + 1):(win + 1), -(win + 1):(win + 1));   % patch incl. 1-pixel gradient margin
xg = 0:W - 1;
yg = 0:H - 1;
eps2 = max(eps_val, 0)^2;

for p = 1:size(pts, 1)
    cT = double(pts(p, :));
    cI = cT;
    for it = 1:max_iter
        gx = min(max(cI(1) + pjj, 0), W - 1);          % replicate border
        gy = min(max(cI(2) + pii, 0), H - 1);
        patch = interp2(xg, yg, img, gx, gy, 'linear');

        tgx = patch(2:end - 1, 3:end) - patch(2:end - 1, 1:end - 2);
        tgy = patch(3:end, 2:end - 1) - patch(1:end - 2, 2:end - 1);
        gxx = tgx .* tgx .* mask;
        gxy = tgx .* tgy .* mask;
        gyy = tgy .* tgy .* mask;

        a = sum(gxx(:));
        b = sum(gxy(:));
        c = sum(gyy(:));
        bb1 = sum(sum(gxx .* jj + gxy .* ii));
        bb2 = sum(sum(gxy .* jj + gyy .* ii));

        det = a * c - b * b;
        if abs(det) <= eps * eps
            break
        end
        scale = 1 / det;
        cI2 = [cI(1) + c * scale * bb1 - b * scale * bb2, ...
               cI(2) - b * scale * bb1 + a * scale * bb2];
        err = sum((cI2 - cI).^2);
        cI = cI2;
        if cI(1) < 0 || cI(1) >= W || cI(2) < 0 || cI(2) >= H
            break
        end
        if err <= eps2
            break
        end
    end
    if abs(cI(1) - cT(1)) > win || abs(cI(2) - cT(2)) > win
        cI = cT;
    end
    pts(p, :) = cI;
end
end
