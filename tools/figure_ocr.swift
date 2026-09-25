// Print the text macOS Vision reads in each image, for figure_render_qc.py.
// Build: swiftc -O figure_ocr.swift -o figure_ocr
// Usage: figure_ocr <image> [<image> ...]
// Output: one line per recognized text line, "<path>\t<text>"; "<path>\t<<unreadable>>" on failure.
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path)\t<<unreadable>>"); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    for obs in req.results ?? [] {
        if let t = obs.topCandidates(1).first?.string { print("\(path)\t\(t)") }
    }
}
