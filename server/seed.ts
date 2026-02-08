import { db } from "./db";
import { projects, projectHistory, commissions, productionLogistics, projectTouches } from "../shared/schema";
import { sql } from "drizzle-orm";
import crypto from "crypto";

const TENANT_ID = "357145e4-b5a1-43e3-a9ba-f8e834b38034";

function uuid() {
  return crypto.randomUUID();
}

function daysAgo(n: number) {
  return new Date(Date.now() - n * 86400000);
}
function daysFromNow(n: number) {
  return new Date(Date.now() + n * 86400000);
}
function dateStr(d: Date) {
  return d.toISOString().split("T")[0];
}

async function seed() {
  console.log("Seeding realistic sample data...\n");

  const sampleProjects = [
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Copper Ridge Family Dentistry",
      status: "New",
      notes: "Wants exterior channel letters and window frost. Reached out via website form.",
      source: "zapier",
      isActiveV3: true,
      primaryContactName: "Dr. Rachel Simmons",
      primaryContactPhone: "(801) 284-9301",
      primaryContactEmail: "rachel@copperridgedental.com",
      siteAddress: "1450 Copper Ridge Dr, Herriman, UT 84096",
      estimatedValue: "5200",
      createdAt: daysAgo(1),
      lastTouched: daysAgo(1),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Lucky Cat Ramen",
      status: "New",
      notes: "New restaurant opening in March. Needs blade sign, window vinyl, and neon open sign.",
      source: "zapier",
      isActiveV3: true,
      primaryContactName: "Tina Nakamura",
      primaryContactPhone: "(385) 217-6543",
      primaryContactEmail: "tina@luckycatramen.com",
      siteAddress: "88 E Broadway, Salt Lake City, UT 84111",
      estimatedValue: "7800",
      createdAt: daysAgo(0),
      lastTouched: daysAgo(0),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Red Rock Realty",
      status: "New",
      notes: "Referred by Palmer Christiansen. Looking for monument sign for new office.",
      source: "referral",
      isActiveV3: true,
      primaryContactName: "Jeff Harmon",
      primaryContactPhone: "(801) 555-7722",
      primaryContactEmail: "jeff@redrockrealty.com",
      siteAddress: "920 State St, Orem, UT 84057",
      createdAt: daysAgo(3),
      lastTouched: daysAgo(3),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Beehive CrossFit",
      status: "Block A",
      notes: "Site survey completed. Large wall mural + exterior sign. Landlord approval needed for building mount.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Marcus Daly",
      primaryContactPhone: "(801) 630-4412",
      primaryContactEmail: "marcus@beehivecrossfit.com",
      siteAddress: "2200 Industrial Blvd, West Jordan, UT 84088",
      estimatedValue: "9500",
      pendingAction: true,
      actionNote: "Get landlord sign-off on building mount location",
      actionDueDate: dateStr(daysFromNow(2)),
      createdAt: daysAgo(8),
      lastTouched: daysAgo(1),
      statusUpdatedAt: daysAgo(5),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Alpine Pediatrics",
      status: "Block A",
      notes: "Wants monument sign with tenant panels and directional wayfinding. Multi-tenant building.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Dr. Wendy Torres",
      primaryContactPhone: "(385) 400-1188",
      primaryContactEmail: "wtorres@alpinepediatrics.com",
      secondaryContactName: "Building Manager - Steve Lund",
      secondaryContactPhone: "(801) 233-5566",
      siteAddress: "775 Alpine Loop Rd, American Fork, UT 84003",
      estimatedValue: "14000",
      pendingAction: true,
      actionNote: "Schedule survey — coordinate with building manager",
      actionDueDate: dateStr(daysFromNow(1)),
      createdAt: daysAgo(5),
      lastTouched: daysAgo(2),
      statusUpdatedAt: daysAgo(4),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Trestle Brewing Company",
      status: "Block B",
      notes: "Full branding package: taproom interior signs, exterior blade sign, A-frame, patio banner. Matt working on concepts.",
      source: "referral",
      isActiveV3: true,
      primaryContactName: "Connor Briggs",
      primaryContactPhone: "(801) 708-3201",
      primaryContactEmail: "connor@trestlebrewing.com",
      siteAddress: "65 Historic Main, Park City, UT 84060",
      estimatedValue: "22000",
      pendingAction: true,
      actionNote: "Follow up with Matt on 3 design concepts — due Friday",
      actionDueDate: dateStr(daysFromNow(3)),
      createdAt: daysAgo(14),
      lastTouched: daysAgo(1),
      statusUpdatedAt: daysAgo(6),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Canyon View Animal Hospital",
      status: "Block C",
      notes: "Proposal sent for illuminated cabinet sign + ADA suite signs. Waiting for board approval at their Tuesday meeting.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Dr. Amy Strickland",
      primaryContactPhone: "(801) 756-2900",
      primaryContactEmail: "amy@canyonviewvet.com",
      siteAddress: "3400 Canyon Rd, Provo, UT 84604",
      estimatedValue: "16500",
      pendingAction: true,
      actionNote: "Board meets Tuesday — follow up Wed morning",
      actionDueDate: dateStr(daysFromNow(4)),
      depositAmount: "8250",
      depositInvoiceRequested: true,
      valueSource: "validated",
      createdAt: daysAgo(21),
      lastTouched: daysAgo(3),
      statusUpdatedAt: daysAgo(7),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Iron Horse Barber Co",
      status: "Block D",
      notes: "Approved proposal. Vintage neon-style LED sign + hand-painted window lettering. Deposit invoice sent.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Dustin Meyers",
      primaryContactPhone: "(385) 999-2104",
      primaryContactEmail: "dustin@ironhorsebarber.com",
      siteAddress: "412 25th Street, Ogden, UT 84401",
      estimatedValue: "11200",
      depositAmount: "5600",
      depositInvoiceRequested: true,
      depositInvoiceSent: true,
      valueSource: "validated",
      pendingAction: true,
      actionNote: "Deposit invoice sent — follow up if no payment by Friday",
      actionDueDate: dateStr(daysFromNow(2)),
      createdAt: daysAgo(30),
      lastTouched: daysAgo(2),
      statusUpdatedAt: daysAgo(5),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Summit Ridge HOA",
      status: "ACTIVE PRODUCTION",
      notes: "Community entrance monument sign. Production started, fabrication in progress at shop. Target install next Thursday.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Karen Hess",
      primaryContactPhone: "(801) 471-8300",
      primaryContactEmail: "khess@summitridgehoa.org",
      secondaryContactName: "Tony Vega (HOA President)",
      secondaryContactPhone: "(801) 471-8301",
      siteAddress: "1 Summit Ridge Entry, Draper, UT 84020",
      estimatedValue: "24000",
      depositAmount: "12000",
      depositReceivedDate: dateStr(daysAgo(14)),
      productionLocked: true,
      valueSource: "validated",
      createdAt: daysAgo(45),
      lastTouched: daysAgo(1),
      statusUpdatedAt: daysAgo(10),
    },
    {
      id: uuid(),
      tenantId: TENANT_ID,
      clientName: "Solstice Spa & Wellness",
      status: "ACTIVE PRODUCTION",
      notes: "Interior suite signs + exterior halo-lit channel letters. Letters shipped, install scheduled Monday.",
      source: "manual",
      isActiveV3: true,
      primaryContactName: "Megan Cho",
      primaryContactPhone: "(385) 312-7788",
      primaryContactEmail: "megan@solsticewellness.com",
      siteAddress: "1600 Foothill Dr, Salt Lake City, UT 84108",
      estimatedValue: "19500",
      depositAmount: "9750",
      depositReceivedDate: dateStr(daysAgo(21)),
      productionLocked: true,
      valueSource: "validated",
      pendingAction: true,
      actionNote: "Confirm Monday install with crew + send night-before reminder to client",
      actionDueDate: dateStr(daysFromNow(0)),
      createdAt: daysAgo(35),
      lastTouched: daysAgo(0),
      statusUpdatedAt: daysAgo(14),
    },
  ];

  for (const proj of sampleProjects) {
    const [created] = await db
      .insert(projects)
      .values(proj as any)
      .returning();

    await db.insert(projectHistory).values({
      projectId: created.id,
      entryType: "CREATED",
      content: `Project created: ${created.clientName}`,
    });

    if (created.status !== "New") {
      await db.insert(projectHistory).values({
        projectId: created.id,
        entryType: "STATUS_CHANGE",
        content: `Status changed to ${created.status}`,
      });

      await db.insert(projectTouches).values({
        projectId: created.id,
        touchType: "note",
        note: `Initial contact — moved to ${created.status}`,
      });
    }

    if (created.status === "ACTIVE PRODUCTION") {
      await db.insert(commissions).values({
        projectId: created.id,
        totalValue: created.estimatedValue,
        depositAmount: (proj as any).depositAmount,
        depositReceivedDate: (proj as any).depositReceivedDate,
        commissionNotes: "",
      } as any);

      await db.insert(productionLogistics).values({
        projectId: created.id,
        targetInstallationDate: dateStr(daysFromNow(created.clientName.includes("Summit") ? 6 : 2)),
        productionStatus: created.clientName.includes("Summit") ? "fabrication" : "ready_to_install",
        paintSamplesApproved: true,
        siteMeasurementsVerified: true,
      } as any);
    }

    if (created.status === "Block D" || created.status === "Block C") {
      await db.insert(commissions).values({
        projectId: created.id,
        totalValue: created.estimatedValue,
        depositAmount: (proj as any).depositAmount || null,
        commissionNotes: "",
      } as any);
    }

    console.log(`  ✓ ${created.clientName} — ${created.status}`);
  }

  console.log("\nSeed complete! Added 10 sample projects.\n");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed error:", err);
  process.exit(1);
});
