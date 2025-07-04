//
//  Format.swift
//  fantasia
//
//  Created by Jack Heart on 3/28/24.
//

import Foundation


struct Format {
    static func date(_ date: Date) -> String {
        let dateFormatter = DateFormatter()

        let calendar = Calendar.current
        let now = Date()
        let startOfNow = calendar.startOfDay(for: now)
        let startOfDate = calendar.startOfDay(for: date)
        
        let components = calendar.dateComponents([.day], from: startOfDate, to: startOfNow)
        guard let day = components.day else { return "Date Error" }
        
        switch day {
        case 0:
            // Today
            dateFormatter.dateStyle = .none
            dateFormatter.timeStyle = .short
            return dateFormatter.string(from: date)
        case 1:
            // Yesterday
            dateFormatter.dateFormat = "'Yesterday' h:mm a"
            return dateFormatter.string(from: date)
        case 2...7:
            // 2-7 Days Ago
            dateFormatter.dateFormat = "\(day) 'Days Ago' h:mm a"
            return dateFormatter.string(from: date)
        default:
            // More than a week ago
            dateFormatter.dateFormat = "yyyy MMM dd h:mm a"
            return dateFormatter.string(from: date)
        }
    }
    
    static func duration(_ seconds: Double) -> String {
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let remainingSeconds = Int(seconds) % 60
        if hours > 0 {
            return String(format: "%02d:%02d:%02d", hours, minutes, remainingSeconds)
        } else if minutes > 0 {
            return String(format: "%02d:%02d", minutes, remainingSeconds)
        } else {
            return String(format: ":%02d", Int(seconds))
        }
    }
}
