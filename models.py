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

