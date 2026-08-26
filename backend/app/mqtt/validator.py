from app.schemas.sensor import TelemetryPayload, ValidatedTelemetry, DataQualityFlag
from datetime import datetime, timezone
from typing import Dict, Any

class TelemetryValidator:
    
    @staticmethod
    def validate(payload: Dict[str, Any]) -> ValidatedTelemetry:
        try:
            # Map mean to soil_moisture for compatibility
            if "soil_moisture_mean" in payload and payload["soil_moisture_mean"] is not None:
                payload["soil_moisture"] = payload["soil_moisture_mean"]
            # Basic schema validation
            raw_data = TelemetryPayload(**payload)
        except Exception as e:
            raise ValueError(f"Invalid payload schema: {e}")
            
        validated = ValidatedTelemetry(**raw_data.model_dump())
        validated.device_timestamp = raw_data.timestamp
        validated.received_at = datetime.now(timezone.utc)
        
        # 1. Zone Validation
        if validated.zone not in ["A", "B"]:
            validated.quality = DataQualityFlag.INVALID
            validated.quality_reason = f"Unknown zone: {validated.zone}"
            return validated
            
        # 2. Timestamp Validation (Future timestamp check)
        now = datetime.now(timezone.utc)
        if validated.timestamp > now:
            validated.quality = DataQualityFlag.INVALID
            validated.quality_reason = "Future timestamp detected"
            return validated
            
        # 3. Range Validation
        reasons = []
        # If calibrated, validate moisture limits
        for sm in [validated.soil_moisture, validated.soil_moisture_1, validated.soil_moisture_2, validated.soil_moisture_mean]:
            if sm is not None and (sm < 0 or sm > 1):
                reasons.append("soil_moisture_out_of_range")
                break
                
        # Validate raw ADC limits
        for adc in [validated.soil_adc_1, validated.soil_adc_2]:
            if adc is not None and (adc < 0 or adc > 4095):
                reasons.append("soil_adc_out_of_range")
                break

        if validated.air_temperature is not None and (validated.air_temperature < -40 or validated.air_temperature > 85):
            reasons.append("air_temp_out_of_range")
            
        if validated.relative_humidity is not None and (validated.relative_humidity < 0 or validated.relative_humidity > 100):
            reasons.append("rh_out_of_range")
            
        for rad in [validated.radiation, validated.rs_incoming, validated.rs_reflected, validated.rns_fao56, validated.rns_measured]:
            if rad is not None and (rad < 0 or rad > 1500):
                reasons.append("radiation_out_of_range")
                break

        if reasons:
            validated.quality = DataQualityFlag.INVALID
            validated.quality_reason = "; ".join(reasons)
            return validated
            
        # Missing critical data check
        if (validated.soil_moisture is None and 
            validated.soil_adc_1 is None and 
            validated.air_temperature is None):
             validated.quality = DataQualityFlag.MISSING
             validated.quality_reason = "Missing critical sensors"
             return validated

        return validated
