select * from runtimereport
where direction = 'inbound' and Stopname ='DXB SUPER GATE' and minute(act_arr) >= 20;


select * from runtimereport
where direction = 'outbound' and Stopname ='DXB SUPER GATE' and minute(actdep) >= 40;


select * from runtimereport
where direction = 'outbound' and Stopname ='Dubai Offshore Zone - Call Center' and minute(actdep) >= 40;

select * from runtimereport
where direction = 'outbound' and Stopname ='Sheikh Zayed Road, Emirates Holidays' and minute(actdep) >= 40;

select * from runtimereport
where direction = 'outbound' and Stopname ='Emirates Engineering Centre' and minute(actdep) >= 20 and minute(actdep) >= 25;

