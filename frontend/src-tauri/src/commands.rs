use std::path::PathBuf;
use std::process::Command;
use serde::{Deserialize, Serialize};

const API_BASE_URL: &str = "http://127.0.0.1:8765";

#[derive(Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub service: String,
    pub version: String,
    pub device: String,
}

#[derive(Serialize, Deserialize)]
pub struct TokenResponse {
    pub token: String,
}

#[derive(Serialize, Deserialize)]
pub struct TranscribeRequest {
    pub file_path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model_size: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub language: Option<String>,
}

#[derive(Serialize, Deserialize)]
pub struct TranscribeResponse {
    pub status: String,
    pub message: String,
    pub output_files: Vec<String>,
}

#[tauri::command]
pub async fn check_health() -> Result<HealthResponse, String> {
    println!("🔍 Rust: check_health command invoked");
    let client = reqwest::Client::new();

    println!("🔍 Rust: Making request to {}/health", API_BASE_URL);
    let response = client
        .get(format!("{}/health", API_BASE_URL))
        .send()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to connect to backend: {}", e);
            println!("❌ Rust: {}", err_msg);
            err_msg
        })?;

    println!("✅ Rust: Got response with status: {}", response.status());

    if !response.status().is_success() {
        let err_msg = format!("Health check failed: {}", response.status());
        println!("❌ Rust: {}", err_msg);
        return Err(err_msg);
    }

    let health_data = response
        .json::<HealthResponse>()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to parse response: {}", e);
            println!("❌ Rust: {}", err_msg);
            err_msg
        })?;

    println!("✅ Rust: Successfully parsed health response");
    Ok(health_data)
}

#[tauri::command]
pub async fn fetch_auth_token() -> Result<String, String> {
    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/token", API_BASE_URL))
        .send()
        .await
        .map_err(|e| format!("Failed to fetch token: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Token fetch failed: {}", response.status()));
    }

    let token_response: TokenResponse = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(token_response.token)
}

#[tauri::command]
pub async fn transcribe_video(
    file_path: String,
    model_size: Option<String>,
    language: Option<String>,
    auth_token: String,
) -> Result<TranscribeResponse, String> {
    let client = reqwest::Client::new();

    let request_body = TranscribeRequest {
        file_path,
        model_size,
        language,
    };

    let response = client
        .post(format!("{}/transcribe", API_BASE_URL))
        .header("Content-Type", "application/json")
        .header("X-Auth-Token", auth_token)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Failed to send request: {}", e))?;

    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("Transcription failed ({}): {}", status, error_text));
    }

    response
        .json::<TranscribeResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

#[derive(Serialize, Deserialize)]
pub struct YoutubeInfoResponse {
    pub title: String,
    pub video_id: String,
    pub duration: f64,
    pub uploader: String,
}

#[tauri::command]
pub async fn fetch_youtube_info(url: String, auth_token: String) -> Result<YoutubeInfoResponse, String> {
    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/youtube-info", API_BASE_URL))
        .query(&[("url", &url), ("token", &auth_token)])
        .send()
        .await
        .map_err(|e| format!("Failed to connect to backend: {}", e))?;

    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!("YouTube info failed ({}): {}", status, error_text));
    }

    response
        .json::<YoutubeInfoResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // 1. Validate and canonicalize the path
    let path_buf = PathBuf::from(&path);

    // 2. Verify the path exists and is a directory
    if !path_buf.exists() {
        return Err("Path does not exist".to_string());
    }

    if !path_buf.is_dir() {
        return Err("Path is not a directory".to_string());
    }

    // 3. Canonicalize to resolve symlinks and relative paths
    let canonical_path = path_buf
        .canonicalize()
        .map_err(|e| format!("Invalid path: {}", e))?;

    // 4. Convert to string - ensures no null bytes or invalid UTF-8
    let safe_path = canonical_path
        .to_str()
        .ok_or("Path contains invalid characters")?;

    // 5. Select command based on platform (compile-time evaluation)
    let cmd = if cfg!(target_os = "macos") {
        "open"
    } else if cfg!(target_os = "windows") {
        "explorer"
    } else if cfg!(target_os = "linux") {
        "xdg-open"
    } else {
        return Err(format!(
            "Opening folders is not supported on this platform ({})",
            std::env::consts::OS
        ));
    };

    // 6. Single execution path for all supported platforms
    Command::new(cmd)
        .arg(safe_path)
        .spawn()
        .map_err(|e| format!("Failed to open folder: {}", e))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_valid_directory() {
        let temp_dir = env::temp_dir();
        let result = open_folder(temp_dir.to_string_lossy().to_string());
        assert!(result.is_ok());
    }

    #[test]
    fn test_nonexistent_directory() {
        let result = open_folder("/nonexistent/path/12345".to_string());
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_file_not_directory() {
        // Create temp file
        let temp_file = env::temp_dir().join("test_file.txt");
        std::fs::write(&temp_file, "test").unwrap();

        let result = open_folder(temp_file.to_string_lossy().to_string());
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not a directory"));

        // Cleanup
        std::fs::remove_file(temp_file).ok();
    }

    #[test]
    fn test_empty_path() {
        let result = open_folder("".to_string());
        assert!(result.is_err());
        // Should fail at path validation
    }
}
