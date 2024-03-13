import SwiftUI

struct RecordTrack: View {
    @StateObject var audioRecorder = AudioRecorder()
    
    var parent: Track?
    var body: some View {
        VStack {
            Spacer()
            RecorderButton(isRecording: audioRecorder.isRecording, start: {
                audioRecorder.start()
            }, stop: {
                audioRecorder.stopAndSave(to: nil)
            })
        }
        .frame(height: audioRecorder.isRecording ? 200 : 100)
    }
    
}

struct RecorderButton: View {
    var isRecording: Bool
    var start: (() -> Void)
    var stop: (() -> Void)
    
    var body: some View {
        Button(action: {
           withAnimation(.easeInOut) {
               if isRecording {
                   stop()
                } else {
                   start()
                }
            }
        }) {
            ZStack {
                Circle()
                    .stroke(lineWidth: 3)
                    .foregroundColor(.gray)
                    .frame(width: 60, height: 60)
                if !isRecording {
                    Circle()
                        .foregroundColor(.red)
                        .frame(width: 50, height: 50)
                } else {
                    RoundedRectangle(cornerRadius: 5)
                        .foregroundColor(.red)
                        .frame(width: 30, height: 30)
                }
            }
        }
    }
}


struct RecordTrack_Previews: PreviewProvider {
    static var previews: some View {
        RecordTrack()
    }
}
