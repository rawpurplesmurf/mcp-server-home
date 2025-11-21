// WAV audio encoder for browser
// Converts raw PCM audio to WAV format compatible with Wyoming Whisper

export class WavEncoder {
  constructor(sampleRate = 16000, numChannels = 1, bitsPerSample = 16) {
    this.sampleRate = sampleRate
    this.numChannels = numChannels
    this.bitsPerSample = bitsPerSample
  }

  // Encode raw PCM Float32Array to WAV Blob
  encodeWAV(samples) {
    const buffer = new ArrayBuffer(44 + samples.length * 2)
    const view = new DataView(buffer)

    // WAV header
    this.writeString(view, 0, 'RIFF')
    view.setUint32(4, 36 + samples.length * 2, true)
    this.writeString(view, 8, 'WAVE')
    this.writeString(view, 12, 'fmt ')
    view.setUint32(16, 16, true) // fmt chunk size
    view.setUint16(20, 1, true) // PCM format
    view.setUint16(22, this.numChannels, true)
    view.setUint32(24, this.sampleRate, true)
    view.setUint32(28, this.sampleRate * this.numChannels * (this.bitsPerSample / 8), true)
    view.setUint16(32, this.numChannels * (this.bitsPerSample / 8), true)
    view.setUint16(34, this.bitsPerSample, true)
    this.writeString(view, 36, 'data')
    view.setUint32(40, samples.length * 2, true)

    // Write PCM samples
    let offset = 44
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    }

    return new Blob([buffer], { type: 'audio/wav' })
  }

  writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }
}
