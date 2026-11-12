
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from pathlib import Path
import json

app = Flask(__name__)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "clinical_data.db"
JSONL_PATH = DATA_DIR / "clinical_data.jsonl"


engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}"
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()



class ClinicalData(Base):
    __tablename__ = "clinical_data"

    id = Column(Integer, primary_key=True)
    patient_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    diagnosis = Column(String, nullable=False)

    
    blood_pressure = Column(String, nullable=False)
    heart_rate = Column(Integer, nullable=False)
    visit_reason = Column(String, nullable=False)



class ClinicalSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_name: str = Field(min_length=1)
    age: int = Field(ge=0, le=120)
    diagnosis: str = Field(min_length=1)

    
    blood_pressure: str = Field(
        pattern=r"^\d{2,3}/\d{2,3}$"
    )
    heart_rate: int = Field(ge=1, le=250)
    visit_reason: str = Field(min_length=1)



Base.metadata.create_all(engine)



@app.route("/clinical/", methods=["POST"])
def add_clinical_record():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    try:
        validated = ClinicalSchema.model_validate(data)
    except ValidationError as error:
        return jsonify({
            "error": "Validation failed",
            "details": error.errors(
                include_context=False,
                include_input=False
            )
        }), 400

    session = SessionLocal()

    try:
        record = ClinicalData(**validated.model_dump())

        session.add(record)
        session.flush()

        
        record_data = {
            "id": record.id,
            **validated.model_dump()
        }

        
        with open(JSONL_PATH, "a", encoding="utf-8") as file:
            file.write(json.dumps(record_data) + "\n")

        session.commit()

        return jsonify({
            "message": "Clinical record added successfully",
            "record": record_data
        }), 201

    except Exception:
        session.rollback()
        app.logger.exception("Failed to save clinical record")
        return jsonify({
            "error": "Unable to save clinical record"
        }), 500

    finally:
        session.close()


@app.route("/clinical/", methods=["GET"])
def get_clinical_records():
    session = SessionLocal()

    try:
        records = session.query(ClinicalData).all()

        results = [
            {
                "id": record.id,
                "patient_name": record.patient_name,
                "age": record.age,
                "diagnosis": record.diagnosis,
                "blood_pressure": record.blood_pressure,
                "heart_rate": record.heart_rate,
                "visit_reason": record.visit_reason
            }
            for record in records
        ]

        return jsonify(results), 200

    finally:
        session.close()


if __name__ == "__main__":
    app.run(debug=True)
