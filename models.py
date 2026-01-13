from datetime import date

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

    shots = db.relationship("Shot", back_populates="image", cascade="all, delete-orphan")

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

