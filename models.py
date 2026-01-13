from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Scope(db.Model):
    """Optical scope used on a rifle."""

    __tablename__ = "scopes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text, nullable=True)

    rifles = db.relationship("Rifle", back_populates="scope")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Scope {self.name}>"


class Rifle(db.Model):
    """Rifle configuration used by an athlete."""

    __tablename__ = "rifles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text, nullable=True)

    scope_id = db.Column(db.Integer, db.ForeignKey("scopes.id"), nullable=False)
    scope = db.relationship("Scope", back_populates="rifles")

    athletes = db.relationship("Athlete", back_populates="rifle")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Rifle {self.name}>"


class Jacket(db.Model):
    """Shooting jacket."""

    __tablename__ = "jackets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text, nullable=True)

    athletes = db.relationship("Athlete", back_populates="jacket")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Jacket {self.name}>"


class Rank(db.Model):
    """Sport rank / classification of an athlete."""

    __tablename__ = "ranks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text, nullable=True)

    athletes = db.relationship("Athlete", back_populates="rank")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Rank {self.name}>"


class Location(db.Model):
    """Shooting range / location."""

    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    note = db.Column(db.Text, nullable=True)

    athletes = db.relationship("Athlete", back_populates="location")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Location {self.name}>"


class Athlete(db.Model):
    """Athlete / shooter with basic equipment assignments."""

    __tablename__ = "athletes"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(10), nullable=False)  # male / female / other
    date_of_birth = db.Column(db.Date, nullable=True)

    rank_id = db.Column(db.Integer, db.ForeignKey("ranks.id"), nullable=True)
    rank = db.relationship("Rank", back_populates="athletes")

    rifle_id = db.Column(db.Integer, db.ForeignKey("rifles.id"), nullable=False)
    rifle = db.relationship("Rifle", back_populates="athletes")

    jacket_id = db.Column(db.Integer, db.ForeignKey("jackets.id"), nullable=False)
    jacket = db.relationship("Jacket", back_populates="athletes")

    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    location = db.relationship("Location", back_populates="athletes")

    team = db.Column(db.String(150), nullable=True)
    phone_number = db.Column(db.String(30), nullable=True)

    def age(self) -> int | None:
        """Return age in years if date_of_birth is set."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Athlete {self.first_name}>"


# ---------------------------------------------------------------------------
# Training / Session models (extensible and mode-agnostic)
# ---------------------------------------------------------------------------

session_athletes = db.Table(
    "session_athletes",
    db.Column("session_id", db.Integer, db.ForeignKey("sessions.id"), primary_key=True),
    db.Column("athlete_id", db.Integer, db.ForeignKey("athletes.id"), primary_key=True),
)


class Session(db.Model):
    """A generic, mode-agnostic session grouping images and shots.

    This can be specialized (e.g. TrainingSession) in the future but should
    remain a reusable core domain entity.
    """

    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)
    mode = db.Column(db.String(50), nullable=False, default="training")
    started_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    finished_at = db.Column(db.DateTime, nullable=True)

    athletes = db.relationship("Athlete", secondary=session_athletes, backref="sessions")
    images = db.relationship("Image", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Session {self.id} ({self.mode})>"


class Image(db.Model):
    """An uploaded image belonging to a session with processing results."""

    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(250), nullable=False)
    original_path = db.Column(db.String(500), nullable=False)
    overlay_path = db.Column(db.String(500), nullable=True)
    scored_path = db.Column(db.String(500), nullable=True)
    ideal_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    session = db.relationship("Session", back_populates="images")

    # Optional assigned athlete for this image (nullable)
    athlete_id = db.Column(db.Integer, db.ForeignKey("athletes.id"), nullable=True)
    athlete = db.relationship("Athlete")
    
    # Optional series for competition mode (nullable)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=True)

    shots = db.relationship("Shot", back_populates="image", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Override init to automatically set session_id from series if provided."""
        super().__init__(**kwargs)
        # Auto-derive session_id from series if series_id is provided but session_id is not
        if self.series_id and not self.session_id:
            from sqlalchemy.orm import object_session
            # If we have a series_id but no session_id, we'll set it after the series is loaded
            # This will be handled in the before_insert event
            pass

    def shots_count(self) -> int:
        return len(self.shots)

    def total_score(self) -> int:
        return sum(s.final_score if s.final_score is not None else s.auto_score for s in self.shots)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "original_path": self.original_path,
            "overlay_path": self.overlay_path,
            "scored_path": self.scored_path,
            "ideal_path": self.ideal_path,
            "shots_count": self.shots_count(),
            "total_score": self.total_score(),
            "athlete_id": self.athlete_id,
            "athlete_name": f"{self.athlete.first_name} {self.athlete.last_name or ''}".strip() if self.athlete else None,
            "session_id": self.session_id,
            "series_id": self.series_id,
        }


class Shot(db.Model):
    """A single detected shot on an image."""

    __tablename__ = "shots"

    id = db.Column(db.Integer, primary_key=True)
    # Map attribute `shot_index` to existing DB column `idx` for compatibility
    shot_index = db.Column('idx', db.Integer, nullable=False)  # index within the image (1..N)

    # Basic physical / visual properties
    center_px = db.Column(db.JSON, nullable=False)
    dx_mm = db.Column(db.Float, nullable=False)
    dy_mm = db.Column(db.Float, nullable=False)
    dist_mm = db.Column(db.Float, nullable=False)
    bullet_radius_px = db.Column(db.Float, nullable=False)

    auto_score = db.Column(db.Integer, nullable=False)
    final_score = db.Column(db.Integer, nullable=True)

    metadata_json = db.Column(db.JSON, nullable=True)

    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False)
    image = db.relationship("Image", back_populates="shots")

    revisions = db.relationship("ShotRevision", back_populates="shot", cascade="all, delete-orphan")

    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "shot_index": self.shot_index,
            "center_px": self.center_px,
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "dist_mm": self.dist_mm,
            "bullet_radius_px": self.bullet_radius_px,
            "auto_score": self.auto_score,
            "final_score": self.final_score,
            "metadata": self.metadata_json,
        }


class ShotRevision(db.Model):
    """Audit record for manual changes to shots (score corrections)."""

    __tablename__ = "shot_revisions"

    id = db.Column(db.Integer, primary_key=True)
    shot_id = db.Column(db.Integer, db.ForeignKey("shots.id"), nullable=False)
    shot = db.relationship("Shot", back_populates="revisions")

    prev_score = db.Column(db.Integer, nullable=False)
    new_score = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<ShotRevision shot={self.shot_id} {self.prev_score}->{self.new_score}>"


# ---------------------------------------------------------------------------
# Competition Mode models
# ---------------------------------------------------------------------------

class Exercise(db.Model):
    """Competition exercise/program with configurable parameters."""
    
    __tablename__ = "exercises"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_series = db.Column(db.Integer, nullable=False)
    shots_per_series = db.Column(db.Integer, nullable=False)
    timing_type = db.Column(db.String(20), nullable=False, default="fixed")  # fixed / variable / mixed
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    
    competitions = db.relationship("Competition", back_populates="exercise")
    
    def __repr__(self) -> str:
        return f"<Exercise {self.name}>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_series": self.total_series,
            "shots_per_series": self.shots_per_series,
            "timing_type": self.timing_type,
            "is_system": self.is_system,
        }


class Competition(db.Model):
    """A competition instance with multiple athletes participating."""
    
    __tablename__ = "competitions"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft / active / finished
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    exercise = db.relationship("Exercise", back_populates="competitions")
    
    athletes = db.relationship("CompetitionAthlete", back_populates="competition", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Competition {self.name} ({self.status})>"
    
    def can_finish(self) -> bool:
        """Check if competition can be finished based on athlete series status."""
        if self.status == "finished":
            return True
        
        for athlete in self.athletes:
            for series in athlete.series:
                if series.status == "active":
                    return False
        return True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat(),
            "exercise": self.exercise.to_dict() if self.exercise else None,
            "can_finish": self.can_finish(),
        }


class CompetitionAthlete(db.Model):
    """Link between competition and athlete with their series."""
    
    __tablename__ = "competition_athletes"
    
    id = db.Column(db.Integer, primary_key=True)
    
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    competition = db.relationship("Competition", back_populates="athletes")
    
    athlete_id = db.Column(db.Integer, db.ForeignKey("athletes.id"), nullable=False)
    athlete = db.relationship("Athlete")
    
    series = db.relationship("Series", back_populates="competition_athlete", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<CompetitionAthlete {self.athlete.first_name} in {self.competition.name}>"
    
    def get_total_score(self) -> int:
        """Calculate total score across all finished series."""
        total = 0
        for series in self.series:
            if series.status in ["finished", "finished_early"]:
                total += series.get_total_score()
        return total
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "athlete": {
                "id": self.athlete.id,
                "first_name": self.athlete.first_name,
                "last_name": self.athlete.last_name,
                "full_name": f"{self.athlete.first_name} {self.athlete.last_name or ''}".strip(),
            } if self.athlete else None,
            "total_score": self.get_total_score(),
            "series_count": len(self.series),
            "finished_series": len([s for s in self.series if s.status in ["finished", "finished_early"]]),
        }


class Series(db.Model):
    """A shooting series for a specific athlete in a competition."""
    
    __tablename__ = "series"
    
    id = db.Column(db.Integer, primary_key=True)
    series_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active / finished / finished_early
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    
    competition_athlete_id = db.Column(db.Integer, db.ForeignKey("competition_athletes.id"), nullable=False)
    competition_athlete = db.relationship("CompetitionAthlete", back_populates="series")
    
    # Link to session for proper data hierarchy
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    session = db.relationship("Session", backref="series")
    
    images = db.relationship("Image", backref="series", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Series {self.series_number} for {self.competition_athlete.athlete.first_name}>"
    
    def get_total_score(self) -> int:
        """Calculate total score from all images in this series."""
        total = 0
        for image in self.images:
            total += image.total_score()
        return total
    
    def get_shots_count(self) -> int:
        """Get total number of shots across all images in this series."""
        count = 0
        for image in self.images:
            count += image.shots_count()
        return count
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "series_number": self.series_number,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat(),
            "total_score": self.get_total_score(),
            "shots_count": self.get_shots_count(),
            "images_count": len(self.images),
            "session_id": self.session_id,
        }


# ---------------------------------------------------------------------------
# SQLAlchemy Event Listeners for Data Integrity
# ---------------------------------------------------------------------------

from sqlalchemy import event

@event.listens_for(Image, 'before_insert')
def set_image_session_id(mapper, connection, target):
    """Automatically set session_id from series if series_id is provided."""
    if target.series_id and not target.session_id:
        # Query series to get its session_id
        result = connection.execute(
            db.text("SELECT session_id FROM series WHERE id = :series_id"),
            {"series_id": target.series_id}
        ).scalar_one_or_none()
        
        if result:
            target.session_id = result
        else:
            raise ValueError(f"Series with id {target.series_id} not found or has no session_id")

@event.listens_for(Series, 'before_insert')
def set_series_session_id(mapper, connection, target):
    """Automatically create a session for competition series if none exists."""
    if not target.session_id:
        # Create a session for the competition
        from datetime import datetime
        
        competition_athlete = connection.execute(
            db.text("""
                SELECT ca.competition_id, ca.athlete_id, c.name as competition_name
                FROM competition_athletes ca
                JOIN competitions c ON ca.competition_id = c.id
                WHERE ca.id = :competition_athlete_id
            """),
            {"competition_athlete_id": target.competition_athlete_id}
        ).fetchone()
        
        if competition_athlete:
            # Insert a new session for this competition
            session_result = connection.execute(
                db.text("""
                    INSERT INTO sessions (mode, name, started_at, finished_at)
                    VALUES ('competition', :name, :started_at, NULL)
                    RETURNING id
                """),
                {
                    "name": f"Competition: {competition_athlete.competition_name}",
                    "started_at": target.created_at or datetime.utcnow()
                }
            )
            target.session_id = session_result.scalar_one()
        else:
            raise ValueError(f"CompetitionAthlete with id {target.competition_athlete_id} not found")

