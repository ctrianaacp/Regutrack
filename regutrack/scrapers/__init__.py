"""Scraper package — registry of all entity scrapers."""

# Group 1 — Grandes Centralizadores
from regutrack.scrapers.group1_centralizadores.suin_juriscol import SuinJuriscolScraper
from regutrack.scrapers.group1_centralizadores.imprenta_nacional import ImprentaNacionalScraper
from regutrack.scrapers.group1_centralizadores.funcion_publica import FuncionPublicaScraper
from regutrack.scrapers.group1_centralizadores.secretaria_juridica import SecretariaJuridicaScraper

# Group 2 — Ministerios y Presidencia
from regutrack.scrapers.group2_ministerios.presidencia import PresidenciaScraper
from regutrack.scrapers.group2_ministerios.minhacienda import MinhaciendaScraper
from regutrack.scrapers.group2_ministerios.minsalud import MinsaludScraper
from regutrack.scrapers.group2_ministerios.mineducacion import MineducacionScraper
from regutrack.scrapers.group2_ministerios.minenergia import MinenergiaScraper
from regutrack.scrapers.group2_ministerios.mintic import MinticScraper
from regutrack.scrapers.group2_ministerios.mintransporte import MintransporteScraper
from regutrack.scrapers.group2_ministerios.mininterior import MininteriorScraper
from regutrack.scrapers.group2_ministerios.minjusticia import MinjusticiaScraper
from regutrack.scrapers.group2_ministerios.mintrabajo import MintrabajuScraper
from regutrack.scrapers.group2_ministerios.minvivienda import MinviviendaScraper

# Group 3 — Organismos de Control
from regutrack.scrapers.group3_control.sic import SICScraper
from regutrack.scrapers.group3_control.superfinanciera import SuperfinancieraScraper
from regutrack.scrapers.group3_control.dian import DIANScraper
from regutrack.scrapers.group3_control.contraloria import ContraloriaScraper
from regutrack.scrapers.group3_control.procuraduria import ProcuradoriaScraper

# Group 4 — Rama Legislativa y Judicial
from regutrack.scrapers.group4_legislativa.senado import SenadoScraper
from regutrack.scrapers.group4_legislativa.corte_constitucional import CorteConstitucionalScraper
from regutrack.scrapers.group4_legislativa.consejo_estado import ConsejoEstadoScraper

# Group 5 — Agencias Nacionales
from regutrack.scrapers.group5_agencias.anh import ANHScraper
from regutrack.scrapers.group5_agencias.ant import ANTScraper
from regutrack.scrapers.group5_agencias.anla import ANLAScraper
from regutrack.scrapers.group5_agencias.ani import ANIScraper
from regutrack.scrapers.group5_agencias.anm import ANMScraper
from regutrack.scrapers.group5_agencias.ansv import ANSVScraper
from regutrack.scrapers.group5_agencias.ane import ANEScraper
from regutrack.scrapers.group5_agencias.creg import CREGScraper

# Group 6 — Entidades Descentralizadas
from regutrack.scrapers.group6_descentralizadas.aerocivil import AerocivilScraper
from regutrack.scrapers.group6_descentralizadas.invias import InviasScraper
from regutrack.scrapers.group6_descentralizadas.dnp import DNPScraper
from regutrack.scrapers.group6_descentralizadas.dane import DANEScraper
from regutrack.scrapers.group6_descentralizadas.icbf import ICBFScraper
from regutrack.scrapers.group6_descentralizadas.upme import UPMEScraper

# Master list — all scrapers in execution order
ALL_SCRAPERS = [
    # Group 1
    SuinJuriscolScraper,
    ImprentaNacionalScraper,
    FuncionPublicaScraper,
    SecretariaJuridicaScraper,
    # Group 2
    PresidenciaScraper,
    MinhaciendaScraper,
    MinsaludScraper,
    MineducacionScraper,
    MinenergiaScraper,
    MinticScraper,
    MintransporteScraper,
    MininteriorScraper,
    MinjusticiaScraper,
    MintrabajuScraper,
    MinviviendaScraper,
    # Group 3
    SICScraper,
    SuperfinancieraScraper,
    DIANScraper,
    ContraloriaScraper,
    ProcuradoriaScraper,
    # Group 4
    SenadoScraper,
    CorteConstitucionalScraper,
    ConsejoEstadoScraper,
    # Group 5
    ANHScraper,
    ANTScraper,
    ANLAScraper,
    ANIScraper,
    ANMScraper,
    ANSVScraper,
    ANEScraper,
    CREGScraper,
    # Group 6
    AerocivilScraper,
    InviasScraper,
    DNPScraper,
    DANEScraper,
    ICBFScraper,
    UPMEScraper,
]

# Lookup by short key (used in CLI --entity flag)
SCRAPERS_BY_KEY: dict[str, type] = {
    # Group 1
    "suin_juriscol": SuinJuriscolScraper,
    "imprenta_nacional": ImprentaNacionalScraper,
    "funcion_publica": FuncionPublicaScraper,
    "secretaria_juridica": SecretariaJuridicaScraper,
    # Group 2
    "presidencia": PresidenciaScraper,
    "minhacienda": MinhaciendaScraper,
    "minsalud": MinsaludScraper,
    "mineducacion": MineducacionScraper,
    "minenergia": MinenergiaScraper,
    "mintic": MinticScraper,
    "mintransporte": MintransporteScraper,
    "mininterior": MininteriorScraper,
    "minjusticia": MinjusticiaScraper,
    "mintrabajo": MintrabajuScraper,
    "minvivienda": MinviviendaScraper,
    # Group 3
    "sic": SICScraper,
    "superfinanciera": SuperfinancieraScraper,
    "dian": DIANScraper,
    "contraloria": ContraloriaScraper,
    "procuraduria": ProcuradoriaScraper,
    # Group 4
    "senado": SenadoScraper,
    "corte_constitucional": CorteConstitucionalScraper,
    "consejo_estado": ConsejoEstadoScraper,
    # Group 5
    "anh": ANHScraper,
    "ant": ANTScraper,
    "anla": ANLAScraper,
    "ani": ANIScraper,
    "anm": ANMScraper,
    "ansv": ANSVScraper,
    "ane": ANEScraper,
    "creg": CREGScraper,
    # Group 6
    "aerocivil": AerocivilScraper,
    "invias": InviasScraper,
    "dnp": DNPScraper,
    "dane": DANEScraper,
    "icbf": ICBFScraper,
    "upme": UPMEScraper,
}


async def run_all_scrapers() -> list:
    """Run all scrapers sequentially, returning list of ScrapeResult."""
    from regutrack.database import get_session
    results = []
    for cls in ALL_SCRAPERS:
        scraper = cls()
        with get_session() as session:
            result = await scraper.run(session)
            results.append(result)
    return results
