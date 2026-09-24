#!/usr/bin/env Rscript
# Render multiple explicit series from build_tree_tracks.py; no assay aggregation.
f <- sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
source(file.path(dirname(normalizePath(f)),'tree_track_render.R'))
render_tree_tracks(commandArgs(trailingOnly=TRUE))
