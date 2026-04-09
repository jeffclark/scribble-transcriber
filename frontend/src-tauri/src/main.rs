// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

// Commands module
mod commands;

// State to track the backend process
struct BackendProcess(Mutex<Option<Child>>);

impl Drop for BackendProcess {
    fn drop(&mut self) {
        println!("🔴 BackendProcess Drop called - terminating backend");
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                println!("✅ Backend terminated in Drop");
            }
        }
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            commands::open_folder,
            commands::check_health,
            commands::fetch_auth_token,
            commands::transcribe_video
        ])
        .setup(|app| {
            let backend_process = app.state::<BackendProcess>();

            // Get path to app's executable directory (Contents/MacOS/)
            let exe_path = std::env::current_exe()
                .expect("failed to get executable path");
            let exe_dir = exe_path.parent()
                .expect("failed to get executable directory");

            // Backend is in the same directory as the main executable
            // Tauri strips the architecture suffix from external binaries
            let backend_binary = exe_dir.join("scribble-backend");

            // Kill any orphaned backend on port 8765 before starting fresh
            let _ = std::process::Command::new("sh")
                .arg("-c")
                .arg("lsof -ti :8765 | xargs kill -9 2>/dev/null || true")
                .output();

            // Start the backend process
            println!("Starting backend at: {:?}", backend_binary);

            if !backend_binary.exists() {
                panic!("Backend binary not found at {:?}", backend_binary);
            }

            // On Unix, create a new process group so we can kill all children
            #[cfg(unix)]
            use std::os::unix::process::CommandExt;

            #[cfg(unix)]
            let mut cmd = Command::new(&backend_binary);
            #[cfg(unix)]
            let cmd = cmd
                .arg("--port")
                .arg("8765")
                .process_group(0); // Create new process group

            #[cfg(not(unix))]
            let cmd = Command::new(&backend_binary)
                .arg("--port")
                .arg("8765");

            let child = cmd.spawn().expect("Failed to start backend");

            // Store the process handle
            *backend_process.0.lock().unwrap() = Some(child);

            println!("✅ Backend process spawned, waiting for it to be ready...");

            // Wait for backend to actually start listening (up to 10 seconds)
            let client = reqwest::blocking::Client::new();
            let mut attempts = 0;
            let max_attempts = 20; // 10 seconds (20 * 500ms)

            while attempts < max_attempts {
                std::thread::sleep(std::time::Duration::from_millis(500));
                match client.get("http://127.0.0.1:8765/health").send() {
                    Ok(response) if response.status().is_success() => {
                        println!("✅ Backend is ready and responding");
                        return Ok(());
                    }
                    _ => {
                        attempts += 1;
                        if attempts < max_attempts {
                            print!(".");
                        }
                    }
                }
            }

            println!("\n⚠️ Backend started but not responding after 10 seconds");
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                println!("App exit requested, terminating backend...");
                // Kill any process on port 8765 (catches the backend + all child processes)
                let _ = std::process::Command::new("sh")
                    .arg("-c")
                    .arg("lsof -ti :8765 | xargs kill -9 2>/dev/null || true")
                    .output();
                // Also kill via stored handle as a fallback
                let backend_process = app_handle.state::<BackendProcess>();
                let mut guard = backend_process.0.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                }
                drop(guard);
                println!("✅ Backend terminated");
            }
        });
}
