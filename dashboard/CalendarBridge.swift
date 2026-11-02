import AppKit
import EventKit

// Read-only application behavior. EventKit calls its read permission "Full Access";
// no save, delete, invitation or event mutation APIs are used here.
let store = EKEventStore()
let folder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Daybook")
let selectionURL = folder.appendingPathComponent("calendar-selection.json")
let outputURL = folder.appendingPathComponent("calendar.json")
let errorURL = folder.appendingPathComponent("calendar-error.txt")
let iso = ISO8601DateFormatter()

func save(_ value: Any, to url: URL) throws {
    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    let bytes = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    try bytes.write(to: url, options: .atomic)
    try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
}

func report(_ message: String) {
    try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    try? message.write(to: errorURL, atomically: true, encoding: .utf8)
}

func exportCalendars(_ ids: [String]) throws {
    let calendars = store.calendars(for: .event).filter { ids.contains($0.calendarIdentifier) }
    let now = Date()
    let start = Calendar.current.date(byAdding: .day, value: -45, to: now)!
    let end = Calendar.current.date(byAdding: .day, value: 14, to: now)!
    let events = calendars.isEmpty ? [] : store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: calendars))
    let values: [[String:Any]] = events.filter {
        !$0.isAllDay && $0.status != .canceled && !($0.attendees?.contains { $0.isCurrentUser && $0.participantStatus == .declined } ?? false)
    }.map { event in
        ["id": (event.eventIdentifier ?? "") + "|" + iso.string(from:event.startDate),
         "title":event.title ?? "Untitled event", "start":iso.string(from:event.startDate),
         "end":iso.string(from:event.endDate),"calendar":event.calendar.title]
    }
    try save(["mode":"mac_calendar", "captured_at":iso.string(from:now),
              "range_start":iso.string(from:start),"range_end":iso.string(from:end),
              "events":values,"calendars":calendars.map { $0.title },
              "message":"Synced from selected Mac calendars. Google calendars sync through Calendar.app."], to:outputURL)
    try? FileManager.default.removeItem(at:errorURL)
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?
    var choices: [NSButton] = []
    var calendars: [EKCalendar] = []
    func applicationDidFinishLaunching(_ notification: Notification) {
        if CommandLine.arguments.contains("--sync") {
            guard EKEventStore.authorizationStatus(for: .event) == .fullAccess else {
                report("Calendar access is not enabled. Use Connect calendars in Daybook."); NSApp.terminate(nil); return
            }
            do {
                let ids = try JSONSerialization.jsonObject(with:Data(contentsOf:selectionURL)) as? [String] ?? []
                try exportCalendars(ids)
            } catch { report(error.localizedDescription) }
            NSApp.terminate(nil)
            return
        }
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps:true)
        store.requestFullAccessToEvents { granted, error in
            DispatchQueue.main.async {
                guard granted else {
                    let message = error?.localizedDescription ?? "Calendar access was not granted. You can enable Daybook Calendar in System Settings → Privacy & Security → Calendars."
                    report(message)
                    let alert = NSAlert(); alert.messageText = "Calendar connection needs permission"; alert.informativeText = message
                    alert.runModal(); NSApp.terminate(nil); return
                }
                self.showSelection()
            }
        }
    }
    func showSelection() {
        calendars = store.calendars(for:.event).sorted { $0.title < $1.title }
        let old = (try? JSONSerialization.jsonObject(with:Data(contentsOf:selectionURL))) as? [String] ?? []
        let panel = NSWindow(contentRect:NSRect(x:0,y:0,width:560,height:480), styleMask:[.titled,.closable], backing:.buffered, defer:false)
        panel.title = "Daybook · Choose calendars"
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 12
        let intro = NSTextField(wrappingLabelWithString:"Choose calendars to show as scheduled time. To add Google, open Calendar → Add Account → Google first. Daybook reads event titles and times; it never changes your events.")
        intro.frame.size.width = 480; stack.addArrangedSubview(intro)
        for calendar in calendars {
            let button = NSButton(checkboxWithTitle:"\(calendar.title) · \(calendar.source.title)", target:nil, action:nil)
            button.state = old.contains(calendar.calendarIdentifier) ? .on : .off
            choices.append(button); stack.addArrangedSubview(button)
        }
        let saveButton = NSButton(title:"Save and sync",target:self,action:#selector(saveSelection)); stack.addArrangedSubview(saveButton)
        let scroll = NSScrollView(frame:panel.contentView!.bounds.insetBy(dx:24,dy:24)); scroll.hasVerticalScroller = true; scroll.autoresizingMask = [.width,.height]
        stack.frame = NSRect(x:0,y:0,width:490,height:CGFloat(130+calendars.count*34)); scroll.documentView = stack
        panel.contentView!.addSubview(scroll)
        window = panel; panel.center(); panel.makeKeyAndOrderFront(nil)
    }
    @objc func saveSelection() {
        do {
            let ids = zip(calendars,choices).filter { $0.1.state == .on }.map { $0.0.calendarIdentifier }
            try save(ids,to:selectionURL); try exportCalendars(ids); NSApp.terminate(nil)
        } catch { report(error.localizedDescription) }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication) -> Bool { true }
}
let delegate = AppDelegate()
NSApplication.shared.delegate = delegate
NSApplication.shared.run()
