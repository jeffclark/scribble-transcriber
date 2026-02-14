use std::path::PathBuf;
use std::process::Command;

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
