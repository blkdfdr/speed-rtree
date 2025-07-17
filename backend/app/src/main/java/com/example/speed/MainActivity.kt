package com.example.speed

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.*
import com.google.android.gms.tasks.CancellationTokenSource
import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class MainActivity : ComponentActivity() {

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var latitude: MutableState<Double?> = mutableStateOf(null)
    private var longitude: MutableState<Double?> = mutableStateOf(null)
    private var speedLimit: MutableState<String?> = mutableStateOf(null)

    private val requestPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
            when {
                permissions.getOrDefault(Manifest.permission.ACCESS_FINE_LOCATION, false) -> {
                    getCurrentLocation()
                }
                permissions.getOrDefault(Manifest.permission.ACCESS_COARSE_LOCATION, false) -> {
                    getCurrentLocation()
                } else -> {
                Toast.makeText(this, "Location permission denied", Toast.LENGTH_SHORT).show()
            }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        setContent {
            LocationApp(
                latitude = latitude.value,
                longitude = longitude.value,
                speedLimit = speedLimit.value,
                onGetLocationClick = { requestLocationPermission() }
            )
        }
    }

    private fun requestLocationPermission() {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED -> {
                getCurrentLocation()
            }
            shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_FINE_LOCATION) ||
                    shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_COARSE_LOCATION) -> {
                Toast.makeText(this, "Location permission is needed to show coordinates", Toast.LENGTH_LONG).show()
                requestPermissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION
                    )
                )
            }
            else -> {
                requestPermissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION
                    )
                )
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun getCurrentLocation() {
        fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, CancellationTokenSource().token)
            .addOnSuccessListener { location: Location? ->
                if (location != null) {
                    latitude.value = location.latitude
                    longitude.value = location.longitude
                    fetchSpeedLimit(location.latitude, location.longitude)
                } else {
                    Toast.makeText(this, "Could not get location. Is GPS enabled?", Toast.LENGTH_SHORT).show()
                    getLastKnownLocation()
                }
            }
            .addOnFailureListener {
                Toast.makeText(this, "Failed to get location: ${it.message}", Toast.LENGTH_SHORT).show()
                getLastKnownLocation()
            }
    }

    @SuppressLint("MissingPermission")
    private fun getLastKnownLocation() {
        fusedLocationClient.lastLocation
            .addOnSuccessListener { location: Location? ->
                if (location != null) {
                    latitude.value = location.latitude
                    longitude.value = location.longitude
                    fetchSpeedLimit(location.latitude, location.longitude)
                    Toast.makeText(this, "Showing last known location.", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "No last known location available.", Toast.LENGTH_SHORT).show()
                }
            }
            .addOnFailureListener {
                Toast.makeText(this, "Failed to get last known location: ${it.message}", Toast.LENGTH_SHORT).show()
            }
    }

    private fun fetchSpeedLimit(lat: Double, lon: Double) {
        val url =
            "https://overpass-api.de/api/interpreter?data=[out:json];way(around:100,$lat,$lon)[highway];out tags;"
        val client = OkHttpClient()
        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("SpeedLimit", "API call failed: ${e.message}")
                runOnUiThread {
                    speedLimit.value = "Unavailable"
                }
            }

            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                if (responseBody == null || !response.isSuccessful) {
                    runOnUiThread {
                        speedLimit.value = "Unavailable"
                    }
                    return
                }

                try {
                    val jsonObj = JSONObject(responseBody)
                    val elements = jsonObj.optJSONArray("elements")
                    var limit: String? = null

                    if (elements != null) {
                        for (i in 0 until elements.length()) {
                            val tags = elements.getJSONObject(i).optJSONObject("tags")
                            if (tags != null && tags.has("maxspeed")) {
                                limit = tags.getString("maxspeed")
                                break
                            }
                        }
                    }

                    runOnUiThread {
                        speedLimit.value = limit ?: "Not found"
                    }
                } catch (e: Exception) {
                    Log.e("SpeedLimit", "Parsing error: ${e.message}")
                    runOnUiThread {
                        speedLimit.value = "Parse error"
                    }
                }
            }
        })
    }
}

@Composable
fun LocationApp(
    latitude: Double?,
    longitude: Double?,
    speedLimit: String?,
    onGetLocationClick: () -> Unit
) {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Button(onClick = onGetLocationClick) {
                    Text("Get Current Location")
                }
                Spacer(modifier = Modifier.height(20.dp))
                Text("Latitude: ${latitude ?: "Loading..."}")
                Text("Longitude: ${longitude ?: "Loading..."}")
                Text("Speed Limit: ${speedLimit ?: "Loading..."}")
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun DefaultPreview() {
    LocationApp(latitude = 48.8588443, longitude = 2.2943506, speedLimit = "50 km/h", onGetLocationClick = {})
}
