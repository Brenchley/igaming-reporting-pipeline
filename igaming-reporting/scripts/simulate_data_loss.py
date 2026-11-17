"""Demo: silently drop 5 settled sportsbook bets from one day in the raw layer (as if a load
lost part of a page) so you can watch reconciliation flag it and the alert fire."""
import os
import duckdb

con = duckdb.connect(os.environ.get("DUCKDB_PATH", "warehouse.duckdb"))
day = con.execute("""select cast(settled_at + interval 2 hour as date) d from raw_crm.bets
                     where status = 'settled' group by 1 order by 1 desc limit 1 offset 3""").fetchone()[0]
ids = [r[0] for r in con.execute("""select bet_id from raw_crm.bets
                                    where product = 'sportsbook' and status = 'settled'
                                      and cast(settled_at + interval 2 hour as date) = ?
                                    order by bet_id limit 5""", [day]).fetchall()]
con.execute(f"delete from raw_crm.bets where bet_id in ({','.join('?' * len(ids))})", ids)
print(f"Deleted {len(ids)} raw sportsbook bets settled on {day}. Now rebuilding and checking...")
