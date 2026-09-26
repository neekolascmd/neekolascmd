import Foundation
import CoreText
import CoreGraphics

// Reads JSON lines {"font","size","text","tracking"?} from stdin and writes JSON lines
// {"d": svg path (baseline at y=0, y down), "w": advance width}.
func fmt(_ v: CGFloat) -> String {
    let r = (v * 10).rounded() / 10
    if r == r.rounded() { return String(Int(r)) }
    return String(format: "%.1f", Double(r))
}

func svgPath(_ path: CGPath) -> String {
    var out = ""
    path.applyWithBlock { el in
        let p = el.pointee.points
        switch el.pointee.type {
        case .moveToPoint: out += "M\(fmt(p[0].x)) \(fmt(p[0].y))"
        case .addLineToPoint: out += "L\(fmt(p[0].x)) \(fmt(p[0].y))"
        case .addQuadCurveToPoint: out += "Q\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y))"
        case .addCurveToPoint: out += "C\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y)) \(fmt(p[2].x)) \(fmt(p[2].y))"
        case .closeSubpath: out += "Z"
        @unknown default: break
        }
    }
    return out
}

while let line = readLine() {
    guard let data = line.data(using: .utf8),
          let req = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let fontName = req["font"] as? String,
          let size = req["size"] as? Double,
          let text = req["text"] as? String else { print("{\"error\":\"bad request\"}"); continue }
    let tracking = req["tracking"] as? Double ?? 0
    let font = CTFontCreateWithName(fontName as CFString, CGFloat(size), nil)
    var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font]
    if tracking != 0 { attrs[NSAttributedString.Key(kCTKernAttributeName as String)] = tracking }
    let str = NSAttributedString(string: text, attributes: attrs)
    let ctLine = CTLineCreateWithAttributedString(str)
    let combined = CGMutablePath()
    for run in CTLineGetGlyphRuns(ctLine) as! [CTRun] {
        let runAttrs = CTRunGetAttributes(run) as NSDictionary
        let runFont = runAttrs[kCTFontAttributeName as String] as! CTFont
        let n = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: n)
        var positions = [CGPoint](repeating: .zero, count: n)
        CTRunGetGlyphs(run, CFRange(location: 0, length: n), &glyphs)
        CTRunGetPositions(run, CFRange(location: 0, length: n), &positions)
        for i in 0..<n {
            var t = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: positions[i].x, ty: -positions[i].y)
            if let gp = CTFontCreatePathForGlyph(runFont, glyphs[i], &t) { combined.addPath(gp) }
        }
    }
    var asc: CGFloat = 0, desc: CGFloat = 0, lead: CGFloat = 0
    let w = CTLineGetTypographicBounds(ctLine, &asc, &desc, &lead)
    // Trailing tracking is added after the last glyph; drop it so centering stays exact.
    let width = CGFloat(w) - (text.isEmpty ? 0 : CGFloat(tracking))
    let res: [String: Any] = ["d": svgPath(combined), "w": Double(width), "capH": Double(CTFontGetCapHeight(font))]
    let out = try! JSONSerialization.data(withJSONObject: res)
    print(String(data: out, encoding: .utf8)!)
    fflush(stdout)
}
