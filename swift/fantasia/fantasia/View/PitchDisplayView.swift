import SwiftUI

struct PitchDisplayView: View {
    let pitch: Pitch?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(pitchText)
                .font(.headline)
            if let pitch = pitch {
                Text("Frequency: \(String(format: "%.2f", pitch.hz)) Hz")
                    .font(.subheadline)
                Text("Cents: \(String(format: "%.0f", pitch.cents))")
                    .font(.subheadline)
                Text("MIDI Note: \(pitch.midiNoteNumber)")
                    .font(.subheadline)
            }
        }
        .padding()
        .background(Color.secondary.opacity(0.1))
        .cornerRadius(8)
    }

    private var pitchText: String {
        if let pitch = pitch {
            return "Pitch: \(pitch.fullName)"
        } else {
            return "No pitch detected"
        }
    }
}

#Preview {
    VStack(spacing: 20) {
        PitchDisplayView(pitch: Pitch(440))
        PitchDisplayView(pitch: Pitch(261.63))
        PitchDisplayView(pitch: nil)
    }
}
