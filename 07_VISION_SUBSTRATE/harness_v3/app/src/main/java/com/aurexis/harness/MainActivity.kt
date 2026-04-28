package com.aurexis.harness

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.aurexis.harness.databinding.ActivityMainBinding
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.BufferedOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Aurexis / Phoxelis Phone Harness v3.0.
 *
 * Five-protocol capture loop. Tap a named protocol, tap CAPTURE.
 * Each photo's per-frame sensor metadata is collected in memory.
 * EXPORT bundles the session's JPEGs + a manifest.json into a
 * `.aurex-session` zip in Downloads/Aurexis/.
 *
 * v3.0 changes (over v2.1):
 *  - new POLARIZATION_PAIR protocol: two bursts at orthogonal phone
 *    orientations (axis 0, then user rotates phone 90 deg, axis 90).
 *    Per-frame axisLabel ("0deg" / "90deg") written to manifest.
 *  - manifest schemaVersion bumped to "aurex-session-1.2" so the
 *    Workbench bridge can branch on axis labels.
 *
 * v2.1 fixes (still in place):
 *  - separate `captureRequested` counter so filenames are unique even
 *    when save callbacks lag behind takePhoto requests
 *  - self-paced burst: next request fires when the previous save
 *    completes (single in-flight)
 *  - manifest reports actual inter-frame median + min/max
 *
 * The five locked protocols (filename-friendly snake_case ids):
 *   static_calibration_grid   - lens distortion + structure-tensor
 *   repetition_strip          - autocorrelation period + weak signal
 *   symmetry_test             - mirror correlation + higher-order coherence
 *   low_light_weak_signal     - ISO 800-3200 noise profile
 *   polarization_pair         - two-axis capture for polarization signal
 */
class MainActivity : AppCompatActivity(), SensorEventListener {

    private lateinit var binding: ActivityMainBinding
    private var imageCapture: ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var sensorManager: SensorManager
    private var accelSensor: Sensor? = null
    private var lightSensor: Sensor? = null

    private val sessionId: String = UUID.randomUUID().toString().take(8)
    private var protocol: Protocol = Protocol.CALIBRATION
    // captureIndex: number of saves *completed*. Source of truth for
    //   header counter, manifest frame_index, and EXPORT readiness.
    private var captureIndex: Int = 0
    // captureRequested: number of takePhoto() *requests* dispatched.
    //   Used for the filename's idx token so filenames are unique even
    //   if save callbacks lag behind. Always >= captureIndex.
    private var captureRequested: Int = 0
    private val captureLog: MutableList<CaptureRecord> = mutableListOf()

    private val mainHandler = Handler(Looper.getMainLooper())
    private var burstActive: Boolean = false
    private var burstRemaining: Int = 0
    private var sessionStartedAtMs: Long = 0L
    private var sessionCompletedAtMs: Long = 0L
    private var inFlight: Int = 0

    // v3.0 polarization-pair state. For non-polarization protocols this
    // stays at "0deg" and the second-axis branch is never taken.
    private var axisInProgress: String = "0deg"
    private var polAxis0Done: Boolean = false

    @Volatile private var lastAccelX: Float = Float.NaN
    @Volatile private var lastAccelY: Float = Float.NaN
    @Volatile private var lastAccelZ: Float = Float.NaN
    @Volatile private var lastLightLux: Float = Float.NaN

    enum class Protocol(val id: String, val labelStringRes: Int,
                          val instructionsStringRes: Int) {
        CALIBRATION("static_calibration_grid",
                     R.string.proto_calibration_label,
                     R.string.proto_calibration_instructions),
        REPETITION("repetition_strip",
                    R.string.proto_repetition_label,
                    R.string.proto_repetition_instructions),
        SYMMETRY("symmetry_test",
                  R.string.proto_symmetry_label,
                  R.string.proto_symmetry_instructions),
        LOW_LIGHT("low_light_weak_signal",
                   R.string.proto_lowlight_label,
                   R.string.proto_lowlight_instructions),
        POLARIZATION_PAIR("polarization_pair",
                           R.string.proto_polarization_label,
                           R.string.proto_polarization_instructions),
    }

    data class CaptureRecord(
        val frameIndex: Int,
        val protocolId: String,
        val capturedAtMs: Long,
        val timestampLabel: String,
        val filename: String,
        val mediaUri: String?,
        val accelX: Float,
        val accelY: Float,
        val accelZ: Float,
        val lightLux: Float,
        val isoSensitivity: Int? = null,
        val exposureTimeNs: Long? = null,
        val focalLengthMm: Float? = null,
        // v3.0: polarization axis label for POLARIZATION_PAIR protocol.
        // null for all other protocols (kept null so older readers
        // that ignore unknown fields still see the same payload shape).
        val axisLabel: String? = null,
    )

    data class SessionManifest(
        val schemaVersion: String = "aurex-session-1.2",
        val sessionId: String,
        val protocolId: String,
        val protocolLabel: String,
        val protocolInstructions: String,
        val targetCount: Int,
        val burstMinIntervalMs: Long,
        val burstActualMedianMs: Long?,
        val burstActualMinMs: Long?,
        val burstActualMaxMs: Long?,
        val startedAtMs: Long,
        val completedAtMs: Long,
        val device: Map<String, String>,
        val camera: Map<String, String>,
        val frames: List<CaptureRecord>,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        lightSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS
            )
        }

        binding.protoCalibrationButton.setOnClickListener {
            setProtocol(Protocol.CALIBRATION)
        }
        binding.protoRepetitionButton.setOnClickListener {
            setProtocol(Protocol.REPETITION)
        }
        binding.protoSymmetryButton.setOnClickListener {
            setProtocol(Protocol.SYMMETRY)
        }
        binding.protoLowLightButton.setOnClickListener {
            setProtocol(Protocol.LOW_LIGHT)
        }
        binding.protoPolarizationButton.setOnClickListener {
            setProtocol(Protocol.POLARIZATION_PAIR)
        }

        binding.captureButton.setOnClickListener {
            if (burstActive) cancelBurst()
            else startBurst(BURST_COUNT)
        }

        binding.exportButton.setOnClickListener { exportSession() }

        applyProtocolToUi()
        updateHeader()
        binding.statusText.text =
            "Ready. Pick a protocol, then tap CAPTURE for a $BURST_COUNT-shot burst."

        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    override fun onResume() {
        super.onResume()
        accelSensor?.let {
            sensorManager.registerListener(
                this, it, SensorManager.SENSOR_DELAY_NORMAL)
        }
        lightSensor?.let {
            sensorManager.registerListener(
                this, it, SensorManager.SENSOR_DELAY_NORMAL)
        }
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                lastAccelX = event.values.getOrNull(0) ?: Float.NaN
                lastAccelY = event.values.getOrNull(1) ?: Float.NaN
                lastAccelZ = event.values.getOrNull(2) ?: Float.NaN
            }
            Sensor.TYPE_LIGHT -> {
                lastLightLux = event.values.getOrNull(0) ?: Float.NaN
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    // -------- Protocol UI -----------------------------------------

    private fun setProtocol(p: Protocol) {
        if (burstActive) {
            binding.statusText.text = "Cancel the current burst before switching protocol."
            return
        }
        protocol = p
        // Switching protocol resets the in-memory session state.
        captureIndex = 0
        captureRequested = 0
        captureLog.clear()
        sessionStartedAtMs = 0L
        sessionCompletedAtMs = 0L
        // v3.0: reset polarization-pair axis state on every protocol switch.
        axisInProgress = "0deg"
        polAxis0Done = false
        binding.exportButton.isEnabled = false
        applyProtocolToUi()
        updateHeader()
        binding.statusText.text =
            "Protocol set: " + getString(p.labelStringRes) +
            ". Read the instructions, then tap CAPTURE."
    }

    private fun applyProtocolToUi() {
        binding.instructionsText.text = getString(protocol.instructionsStringRes)
    }

    private fun updateHeader() {
        val total =
            if (protocol == Protocol.POLARIZATION_PAIR) BURST_COUNT * 2
            else BURST_COUNT
        val axisTag =
            if (protocol == Protocol.POLARIZATION_PAIR) "  |  axis $axisInProgress"
            else ""
        binding.sessionText.text =
            "Session: $sessionId  |  ${getString(protocol.labelStringRes)}$axisTag  |  " +
            "Captures: $captureIndex / $total"
    }

    // -------- Burst (v2.1 self-paced) -----------------------------

    private fun startBurst(count: Int) {
        if (imageCapture == null) {
            binding.statusText.text = "Camera not ready yet."
            return
        }
        // v3.0: polarization-pair second-axis branch keeps the existing
        // captureLog so the manifest contains all 60 frames.
        val polMidway = protocol == Protocol.POLARIZATION_PAIR && polAxis0Done
        burstActive = true
        burstRemaining = count
        inFlight = 0
        if (!polMidway) {
            captureIndex = 0
            captureRequested = 0
            captureLog.clear()
            sessionStartedAtMs = System.currentTimeMillis()
        }
        sessionCompletedAtMs = 0L
        binding.exportButton.isEnabled = false
        binding.captureButton.text = "STOP BURST"
        val totalTarget =
            if (protocol == Protocol.POLARIZATION_PAIR) BURST_COUNT * 2
            else BURST_COUNT
        binding.statusText.text =
            "Capturing $captureIndex / $totalTarget [$axisInProgress] ..."
        // Kick off the first request; subsequent requests are driven
        // by save callbacks so we don't queue faster than HAL can save.
        requestNextShot()
    }

    private fun requestNextShot() {
        if (!burstActive) {
            tryFinishBurst()
            return
        }
        if (burstRemaining <= 0) {
            tryFinishBurst()
            return
        }
        if (inFlight >= MAX_IN_FLIGHT) {
            // Wait for current save to release a slot.
            return
        }
        captureRequested += 1
        burstRemaining -= 1
        inFlight += 1
        takePhoto(captureRequested)
    }

    private fun tryFinishBurst() {
        if (burstRemaining <= 0 && inFlight <= 0) {
            finishBurst()
        }
    }

    private fun cancelBurst() {
        burstActive = false
        burstRemaining = 0
        mainHandler.removeCallbacksAndMessages(null)
        binding.captureButton.text = "START CAPTURE SESSION"
        sessionCompletedAtMs = System.currentTimeMillis()
        if (captureIndex > 0) {
            binding.exportButton.isEnabled = true
            binding.statusText.text =
                "Burst cancelled at $captureIndex. EXPORT enabled."
        } else {
            binding.statusText.text = "Burst cancelled."
        }
    }

    private fun finishBurst() {
        burstActive = false
        burstRemaining = 0
        binding.captureButton.text = "START CAPTURE SESSION"

        // v3.0: polarization-pair mid-state. After axis 0 completes,
        // do NOT mark the session complete or enable EXPORT — instead,
        // prompt Vincent to rotate and tap CAPTURE again for axis 90.
        if (protocol == Protocol.POLARIZATION_PAIR && !polAxis0Done) {
            polAxis0Done = true
            axisInProgress = "90deg"
            binding.exportButton.isEnabled = false
            binding.statusText.text =
                "Axis 0 done ($captureIndex frames). Rotate phone 90° " +
                "clockwise around the lens axis, then tap CAPTURE for axis 90."
            return
        }

        sessionCompletedAtMs = System.currentTimeMillis()
        binding.exportButton.isEnabled = (captureIndex > 0)
        val total =
            if (protocol == Protocol.POLARIZATION_PAIR) BURST_COUNT * 2
            else BURST_COUNT
        binding.statusText.text =
            "Session complete: $captureIndex / $total. Tap EXPORT."
    }

    // -------- Camera ----------------------------------------------

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            imageCapture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build()
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageCapture)
            } catch (exc: Exception) {
                binding.statusText.text = "Camera bind failed: ${exc.message}"
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun takePhoto(requestedOrdinal: Int) {
        val imageCapture = imageCapture ?: run {
            binding.statusText.text = "Camera not ready."
            return
        }

        val timestamp = SimpleDateFormat(FILENAME_FORMAT, Locale.US).format(Date())
        // v2.1: use captureRequested for the filename idx, not captureIndex.
        // captureIndex only increments inside onImageSaved (async), and
        // multiple takePhoto calls can fire before the first save lands.
        val name =
            "AUREXIS_${sessionId}_${protocol.id}_${"%04d".format(requestedOrdinal)}_$timestamp"

        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, name)
            put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.RELATIVE_PATH,
                    "Pictures/Aurexis")
            }
        }

        val outputOptions = ImageCapture.OutputFileOptions.Builder(
            contentResolver,
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            contentValues
        ).build()

        // Snapshot sensor state at capture-request time
        val accelX = lastAccelX
        val accelY = lastAccelY
        val accelZ = lastAccelZ
        val lux    = lastLightLux

        imageCapture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onError(exc: ImageCaptureException) {
                    inFlight -= 1
                    binding.statusText.text =
                        "Capture failed at $requestedOrdinal: ${exc.message}"
                    // Try to keep the burst alive
                    if (burstActive) {
                        if (burstRemaining > 0) {
                            mainHandler.postDelayed(
                                { requestNextShot() }, BURST_MIN_INTERVAL_MS)
                        } else {
                            tryFinishBurst()
                        }
                    }
                }

                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    captureIndex += 1
                    inFlight -= 1
                    val axisForRecord =
                        if (protocol == Protocol.POLARIZATION_PAIR) axisInProgress
                        else null
                    val rec = CaptureRecord(
                        frameIndex = captureIndex,
                        protocolId = protocol.id,
                        capturedAtMs = System.currentTimeMillis(),
                        timestampLabel = timestamp,
                        filename = name + ".jpg",
                        mediaUri = output.savedUri?.toString(),
                        accelX = accelX,
                        accelY = accelY,
                        accelZ = accelZ,
                        lightLux = lux,
                        axisLabel = axisForRecord,
                    )
                    captureLog.add(rec)
                    updateHeader()
                    val totalTarget =
                        if (protocol == Protocol.POLARIZATION_PAIR) BURST_COUNT * 2
                        else BURST_COUNT
                    val axisTag =
                        if (protocol == Protocol.POLARIZATION_PAIR) " [$axisInProgress]"
                        else ""
                    binding.statusText.text =
                        "Capturing $captureIndex / $totalTarget$axisTag ..."
                    // v2.1: drive next request from the save callback.
                    if (burstActive) {
                        if (burstRemaining > 0) {
                            mainHandler.postDelayed(
                                { requestNextShot() }, BURST_MIN_INTERVAL_MS)
                        } else {
                            tryFinishBurst()
                        }
                    }
                }
            }
        )
    }

    // -------- Export ---------------------------------------------

    private fun exportSession() {
        if (captureLog.isEmpty()) {
            binding.statusText.text = "No frames in session."
            return
        }
        binding.statusText.text = "Exporting session ..."
        cameraExecutor.execute {
            try {
                val pair = writeAurexSessionZip()
                runOnUiThread {
                    binding.statusText.text = "Exported: ${pair.second}"
                    Toast.makeText(this,
                        "Saved to Downloads/Aurexis/\n${pair.second}",
                        Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    binding.statusText.text =
                        "Export failed: ${e.message}"
                }
            }
        }
    }

    private fun computeIntervalStats(): Triple<Long?, Long?, Long?> {
        val times = captureLog.map { it.capturedAtMs }.sorted()
        if (times.size < 2) return Triple(null, null, null)
        val deltas = (1 until times.size).map { times[it] - times[it - 1] }
        val sorted = deltas.sorted()
        val median = sorted[sorted.size / 2]
        return Triple(median, sorted.first(), sorted.last())
    }

    private fun writeAurexSessionZip(): Pair<Uri, String> {
        val displayName =
            "AUREXIS_${sessionId}_${protocol.id}.aurex-session"

        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
            put(MediaStore.MediaColumns.MIME_TYPE, "application/zip")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Downloads.RELATIVE_PATH,
                    "Download/Aurexis")
            }
        }

        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Downloads.EXTERNAL_CONTENT_URI
        } else {
            @Suppress("DEPRECATION")
            MediaStore.Files.getContentUri("external")
        }

        val zipUri = contentResolver.insert(collection, values)
            ?: throw RuntimeException("MediaStore insert failed")

        val gson: Gson = GsonBuilder().setPrettyPrinting().serializeNulls().create()
        val (median, mn, mx) = computeIntervalStats()
        val manifest = SessionManifest(
            sessionId = sessionId,
            protocolId = protocol.id,
            protocolLabel = getString(protocol.labelStringRes),
            protocolInstructions = getString(protocol.instructionsStringRes),
            targetCount =
                if (protocol == Protocol.POLARIZATION_PAIR) BURST_COUNT * 2
                else BURST_COUNT,
            burstMinIntervalMs = BURST_MIN_INTERVAL_MS,
            burstActualMedianMs = median,
            burstActualMinMs = mn,
            burstActualMaxMs = mx,
            startedAtMs = sessionStartedAtMs,
            completedAtMs =
                if (sessionCompletedAtMs > 0) sessionCompletedAtMs
                else System.currentTimeMillis(),
            device = mapOf(
                "manufacturer" to (Build.MANUFACTURER ?: ""),
                "model"        to (Build.MODEL ?: ""),
                "android_release" to (Build.VERSION.RELEASE ?: "