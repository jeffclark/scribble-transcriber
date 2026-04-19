import type { TranscribeResponse } from '../types/transcription';

interface ProgressData {
  stage: string;
  progress: number;
  message: string;
  segment_count?: number;
  estimated_total_segments?: number;
  current_time?: number;
  output_files?: {
    json: string;
    txt: string;
  };
  metadata?: {
    source_file: string;
    language: string;
    duration_seconds: number;
  };
  result?: TranscribeResponse;  // Optional - only for small results
}

interface TranscriptionProgressOptions {
  filePath?: string;
  youtubeUrl?: string;
  modelSize: string;
  beamSize: number;
  authToken: string;
  onProgress: (progress: number, message: string, segmentCount?: number, estimatedTotal?: number) => void;
  onComplete: (result: TranscribeResponse) => void;
  onError: (error: string) => void;
}

/**
 * Subscribe to transcription progress via Server-Sent Events.
 * Returns a promise that resolves when transcription completes or rejects on error.
 */
export function transcribeWithProgress(options: TranscriptionProgressOptions): Promise<TranscribeResponse> {
  const { filePath, youtubeUrl, modelSize, beamSize, authToken, onProgress, onComplete, onError } = options;

  return new Promise<TranscribeResponse>((resolve, reject) => {
    // Build query string — exactly one of file_path or youtube_url must be set
    const params = new URLSearchParams({
      model_size: modelSize,
      beam_size: beamSize.toString(),
      token: authToken, // Note: EventSource doesn't support custom headers
    });
    if (youtubeUrl) {
      params.set("youtube_url", youtubeUrl);
    } else {
      params.set("file_path", filePath!);
    }

    const url = `http://127.0.0.1:8765/transcribe-stream?${params}`;

    console.log(`🔌 Opening SSE connection: ${url.split('token=')[0]}token=***`);
    console.log(`🔌 Full URL (for debugging):`, url);

    let eventSource: EventSource;
    try {
      eventSource = new EventSource(url);
      console.log('🔌 EventSource object created:', eventSource.readyState);
    } catch (err) {
      console.error('❌ Failed to create EventSource:', err);
      onError(`Failed to create SSE connection: ${err}`);
      reject(new Error(`Failed to create SSE connection: ${err}`));
      return;
    }

    eventSource.addEventListener('message', (event) => {
      try {
        const data: ProgressData = JSON.parse(event.data);

        // Enhanced logging with timestamp
        console.log('📡 SSE message:', {
          stage: data.stage,
          progress: data.progress,
          message: data.message,
          segmentCount: data.segment_count,
          timestamp: new Date().toISOString()
        });

        switch (data.stage) {
          case 'connecting':
            // Initial connection message (prevents buffering)
            console.log('📡 Connection confirmed by backend');
            break;

          case 'downloading':
          case 'validating':
          case 'extracting':
          case 'loading':
          case 'transcribing':
          case 'saving':
            console.log(`✅ Calling onProgress(${data.progress}, "${data.message}", ${data.segment_count}, ${data.estimated_total_segments})`);
            onProgress(data.progress, data.message, data.segment_count, data.estimated_total_segments);
            break;

          case 'completed':
            console.log('✅ Transcription completed, constructing result from metadata...');
            eventSource.close();

            try {
              // For large transcriptions, backend only sends metadata and file paths
              // Construct the result object from this lightweight data
              if (!data.output_files || !data.metadata) {
                throw new Error('Missing output files or metadata in completion message');
              }

              const result: TranscribeResponse = {
                metadata: {
                  source_file: data.metadata.source_file,
                  transcription_date: new Date().toISOString(),
                  model: 'base',
                  device: 'cpu',
                  language: data.metadata.language,
                  language_probability: 0.99,
                  duration_seconds: data.metadata.duration_seconds,
                },
                segments: [], // Empty - segments are in the JSON file, not needed in UI
                output_files: data.output_files,
              };

              console.log('✅ Result constructed successfully', {
                segments: data.segment_count,
                files: data.output_files
              });

              onProgress(100, 'Complete');
              onComplete(result);
              resolve(result);
            } catch (err) {
              const error = `Failed to process completion: ${err}`;
              console.error('❌', error);
              onError(error);
              reject(new Error(error));
            }
            break;

          case 'error':
            console.error('❌ Transcription error:', data.message);
            onError(data.message);
            eventSource.close();
            reject(new Error(data.message));
            break;

          default:
            console.warn('Unknown stage:', data.stage);
        }
      } catch (err) {
        const error = 'Failed to parse SSE message';
        console.error(error, err);
        onError(error);
        eventSource.close();
        reject(new Error(error));
      }
    });

    eventSource.addEventListener('error', (err) => {
      console.error('❌ SSE connection error:', {
        readyState: eventSource.readyState,
        error: err,
        url: eventSource.url
      });

      // ReadyState values: 0=CONNECTING, 1=OPEN, 2=CLOSED
      if (eventSource.readyState === EventSource.CLOSED) {
        const error = 'Connection to backend closed unexpectedly';
        console.error('❌', error);
        onError(error);
        reject(new Error(error));
      } else if (eventSource.readyState === EventSource.CONNECTING) {
        console.warn('⚠️ SSE connection is retrying...');
        // EventSource will auto-retry, so don't reject yet
      }
    });

    eventSource.addEventListener('open', () => {
      console.log('✅ SSE connection established', {
        readyState: eventSource.readyState,
        url: eventSource.url
      });
    });
  });
}
