import SwiftUI

struct WaveformContentView: View {
    let amplitudes: [CGFloat]
    let barWidth: CGFloat
    let barSpacing: CGFloat
    let scaleX: CGFloat
    let scaleY: CGFloat
    let fillColor: Color
    
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                for (index, amplitude) in amplitudes.enumerated() {
                    let x = CGFloat(index) * (barWidth + barSpacing) * scaleX
                    let height = amplitude * scaleY
                    let y = (geometry.size.height - height) / 2
                    
                    path.move(to: CGPoint(x: x, y: y))
                    path.addLine(to: CGPoint(x: x, y: y + height))
                }
            }
            .stroke(fillColor, lineWidth: barWidth * scaleX)
        }
    }
}
